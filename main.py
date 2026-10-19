
import json
import queue
import socket
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from collections import deque

import psutil
from flask import Flask, jsonify, Response
from flask_sock import Sock
from vosk import Model, KaldiRecognizer, SetLogLevel

# ---------------- CONFIG ----------------

UDP_PORT = 3333
WEB_PORT = 5000
RATE = 16000

MODEL_NAME = "vosk-model-small-en-us-0.15"
MODEL_URL = (
    "https://alphacephei.com/vosk/models/"
    + MODEL_NAME + ".zip"
)

BASE = Path(__file__).resolve().parent
MODEL_DIR = BASE / MODEL_NAME
ZIP_FILE = BASE / (MODEL_NAME + ".zip")

# ----------------------------------------

SetLogLevel(-1)

app = Flask(__name__)
sock = Sock(app)

lock = threading.Lock()
clients = []
history = deque(maxlen=100)

stats = {
    "status": "Starting",
    "packets": 0,
    "bytes": 0,
    "packet_rate": 0,
    "audio_level": 0,
    "cpu_process": 0,
    "cpu_system": 0,
    "ram_process": 0,
    "ram_system": 0,
    "ram_total": 0,
    "partial": "",
    "final": "",
    "speaker": "Not enabled"
}

started = time.time()
last_stats = time.time()
last_packets = 0


def ensure_model():
    if (MODEL_DIR / "am").is_dir():
        print("English model already installed.")
        return

    print("Downloading small English model...")
    urllib.request.urlretrieve(MODEL_URL, ZIP_FILE)

    print("Extracting model...")
    with zipfile.ZipFile(ZIP_FILE) as z:
        z.extractall(BASE)

    ZIP_FILE.unlink(missing_ok=True)

    if not (MODEL_DIR / "am").is_dir():
        raise RuntimeError("Model installation failed")


def set_status(text):
    with lock:
        stats["status"] = text


def broadcast_audio(data):
    with lock:
        targets = list(clients)

    for q in targets:
        try:
            q.put_nowait(data)
        except queue.Full:
            try:
                q.get_nowait()
                q.put_nowait(data)
            except (queue.Empty, queue.Full):
                pass


def udp_receiver(model):
    global last_packets

    rec = KaldiRecognizer(model, RATE)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    udp.bind(("0.0.0.0", UDP_PORT))
    udp.settimeout(1)

    print("UDP receiver ready on port", UDP_PORT)

    while True:
        try:
            data, addr = udp.recvfrom(4096)
        except socket.timeout:
            continue
        except OSError as e:
            print("UDP error:", e)
            time.sleep(0.5)
            continue

        data = data[:len(data) - len(data) % 2]
        if not data:
            continue

        # Forward audio to browser listeners.
        broadcast_audio(data)

        # Calculate a lightweight audio level.
        import array
        samples = array.array("h")
        samples.frombytes(data)
        peak = max((abs(x) for x in samples), default=0)
        level = min(100, int(peak * 100 / 32768))

        with lock:
            stats["packets"] += 1
            stats["bytes"] += len(data)
            stats["audio_level"] = level
            stats["status"] = "Receiving audio"
            stats["source"] = addr[0]

        # Live English STT.
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()

            if text:
                with lock:
                    stats["final"] = (
                        stats["final"] + " " + text
                    ).strip()[-10000:]
                    history.append({
                        "time": time.strftime("%H:%M:%S"),
                        "text": text
                    })
                    stats["partial"] = ""
        else:
            result = json.loads(rec.PartialResult())
            with lock:
                stats["partial"] = result.get("partial", "")


def monitor():
    global last_stats, last_packets

    proc = psutil.Process()
    proc.cpu_percent(None)

    while True:
        time.sleep(1)

        try:
            cpu_proc = proc.cpu_percent(None)
            cpu_sys = psutil.cpu_percent(None)
            ram_proc = proc.memory_info().rss / 1048576
            mem = psutil.virtual_memory()

            with lock:
                now = time.time()
                elapsed = max(0.1, now - last_stats)
                packets = stats["packets"]

                stats["packet_rate"] = round(
                    (packets - last_packets) / elapsed, 1
                )
                stats["cpu_process"] = round(cpu_proc, 1)
                stats["cpu_system"] = round(cpu_sys, 1)
                stats["ram_process"] = round(ram_proc, 1)
                stats["ram_system"] = round(mem.used / 1048576, 1)
                stats["ram_total"] = round(mem.total / 1048576, 1)
                stats["uptime"] = int(now - started)

                last_packets = packets
                last_stats = now

        except Exception as e:
            print("Monitor error:", e)


@app.route("/")
def index():
    return Response(PAGE, mimetype="text/html")


@app.route("/api")
def api():
    with lock:
        return jsonify({
            **stats,
            "history": list(history)
        })


@sock.route("/audio")
def audio_stream(ws):
    q = queue.Queue(maxsize=12)

    with lock:
        clients.append(q)

    try:
        while True:
            try:
                data = q.get(timeout=1)
                ws.send(data)
            except queue.Empty:
                continue
            except Exception:
                break
    finally:
        with lock:
            if q in clients:
                clients.remove(q)


PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Audio Monitor</title>
<style>
:root {
  color-scheme: dark;
  --bg:#0a0f1c;
  --card:#121b2c;
  --line:#26354a;
  --text:#edf3ff;
  --muted:#8da1bd;
  --green:#42e6a4;
  --blue:#65aaff;
}
* { box-sizing:border-box }
body {
  margin:0;
  background:radial-gradient(ellipse at top,#172743,var(--bg) 65%);
  color:var(--text);
  font:14px system-ui, sans-serif;
}
main { max-width:1100px; margin:auto; padding:25px 18px 45px }
header { display:flex; justify-content:space-between;
  align-items:center; gap:15px; flex-wrap:wrap; margin-bottom:24px }
h1 { margin:0; font-size:25px; letter-spacing:-.5px }
.sub { color:var(--muted); margin-top:5px }
.pill { border:1px solid var(--line); border-radius:30px;
  padding:8px 12px; color:var(--green); background:#10251f }
.dot { display:inline-block; width:8px; height:8px;
  border-radius:50%; background:var(--green); margin-right:7px }
.grid { display:grid; grid-template-columns:repeat(4,1fr); gap:13px }
.card { background:linear-gradient(145deg,#172338,#111a2a);
  border:1px solid var(--line); border-radius:15px; padding:17px;
  min-width:0; box-shadow:0 8px 28px #0002 }
.label { color:var(--muted); font-size:12px }
.value { font-size:27px; font-weight:650; margin:8px 0 }
.unit { font-size:12px; color:var(--muted); font-weight:400 }
.bar { height:5px; background:#27364a; border-radius:5px;
  overflow:hidden; margin-top:10px }
.fill { height:100%; width:0; background:var(--green);
  border-radius:5px; transition:width .25s }
.section { margin-top:16px }
.section h2 { font-size:15px; margin:0 0 13px }
.controls { display:flex; gap:10px; flex-wrap:wrap }
button { border:1px solid var(--line); border-radius:9px;
  padding:10px 17px; background:#22314a; color:var(--text);
  font-weight:600; cursor:pointer }
button.primary { background:var(--green); color:#06251a; border:0 }
button:hover { filter:brightness(1.12) }
.level { height:10px; background:#25344b; border-radius:10px;
  overflow:hidden; margin-top:12px }
#level { height:100%; width:0; background:linear-gradient(90deg,
  #42e6a4,#d6ef65,#ff8c69); transition:width .1s }
.transcript { min-height:210px; max-height:390px; overflow:auto;
  white-space:pre-wrap; line-height:1.85; font-size:16px }
#partial { color:var(--blue) }
.meta { color:var(--muted); font-size:12px; margin-top:12px }
.tag { color:var(--blue); font-size:11px; border:1px solid #2c5078;
  border-radius:5px; padding:3px 6px }
.two { display:grid; grid-template-columns:1.5fr 1fr; gap:13px }
#events { max-height:210px; overflow:auto; color:var(--muted);
  line-height:1.8; overflow-wrap:anywhere }
footer { color:var(--muted); font-size:12px; margin-top:20px }
@media(max-width:720px) {
  .grid { grid-template-columns:repeat(2,minmax(0,1fr)) }
  .two { grid-template-columns:1fr }
  h1 { font-size:21px }
}
</style>
</head>
<body>
<main>
<header>
  <div>
    <h1>◉ Audio Monitor</h1>
    <div class="sub">ESP32-S3 · Live English transcription</div>
  </div>
  <div class="pill"><span class="dot"></span><span id="status">Starting</span></div>
</header>

<div class="grid">
  <div class="card">
    <div class="label">APP CPU</div>
    <div class="value"><span id="pcpu">0</span><span class="unit"> %</span></div>
    <div class="bar"><div class="fill" id="pcpubar"></div></div>
  </div>
  <div class="card">
    <div class="label">SYSTEM CPU</div>
    <div class="value"><span id="scpu">0</span><span class="unit"> %</span></div>
    <div class="bar"><div class="fill" id="scpubar"></div></div>
  </div>
  <div class="card">
    <div class="label">APP MEMORY</div>
    <div class="value"><span id="pram">0</span><span class="unit"> MB</span></div>
    <div class="bar"><div class="fill" id="prambar"></div></div>
  </div>
  <div class="card">
    <div class="label">SYSTEM MEMORY</div>
    <div class="value"><span id="sram">0</span><span class="unit"> %</span></div>
    <div class="bar"><div class="fill" id="srambar"></div></div>
    <div class="meta" id="ramdetail">-- MB used</div>
  </div>
</div>

<div class="section card">
  <h2>🎙 Audio input</h2>
  <div class="controls">
    <button class="primary" id="play">▶ Play audio</button>
    <button id="stop">■ Stop</button>
    <span class="tag" id="packets">0 packets/s</span>
    <span class="tag" id="source">No source</span>
  </div>
  <div class="level"><div id="level"></div></div>
  <div class="meta">Input signal level · 16 kHz · 16-bit mono PCM</div>
</div>

<div class="section two">
  <div class="card">
    <h2>✦ Live transcription <span class="tag">ENGLISH</span></h2>
    <div id="final" class="transcript"></div>
    <div id="partial"></div>
    <div class="meta">Partial words may change until a phrase is finalized.</div>
  </div>
  <div class="card">
    <h2>◷ Recent phrases</h2>
    <div id="events">Waiting for speech...</div>
    <div class="meta">Speaker identification: not enabled</div>
  </div>
</div>

<footer>
  Local offline STT · <span id="uptime">0s</span> uptime ·
  Audio is processed on this machine.
</footer>
</main>

<script>
const $ = id => document.getElementById(id);

async function refresh() {
  try {
    const r = await fetch("/api");
    const d = await r.json();

    $("status").textContent = d.status;
    $("pcpu").textContent = d.cpu_process;
    $("scpu").textContent = d.cpu_system;
    $("pram").textContent = d.ram_process;
    $("sram").textContent = d.ram_total
      ? Math.round(d.ram_system * 100 / d.ram_total) : 0;

    $("pcpubar").style.width = Math.min(100,d.cpu_process) + "%";
    $("scpubar").style.width = Math.min(100,d.cpu_system) + "%";
    $("prambar").style.width =
      Math.min(100,d.ram_process / 1024 * 100) + "%";
    $("srambar").style.width = $("sram").textContent + "%";

    $("ramdetail").textContent =
      d.ram_system + " / " + d.ram_total + " MB used";

    $("packets").textContent = d.packet_rate + " packets/s";
    $("source").textContent = d.source || "No source";
    $("level").style.width = d.audio_level + "%";
    $("final").textContent = d.final || "";
    $("partial").textContent = d.partial || "";
    $("uptime").textContent = Math.floor(d.uptime / 60) +
      "m " + (d.uptime % 60) + "s";

    const ev = d.history || [];
    $("events").innerHTML = ev.slice().reverse().map(x =>
      "<div><span class='tag'>" + x.time + "</span> " +
      escapeHTML(x.text) + "</div>"
    ).join("") || "Waiting for speech...";
  } catch(e) {
    $("status").textContent = "Backend disconnected";
  }
}

function escapeHTML(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    "&":"&amp;", "<":"&lt;", ">":"&gt;",
    '"':"&quot;", "'":"&#39;"
  }[c]));
}

setInterval(refresh, 1000);
refresh();

let ctx = null, proc = null, ws = null, playing = false;
let audioQueue = [], offset = 0;

$("play").onclick = async () => {
  if (playing) return;

  try {
    ctx = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 16000
    });
    await ctx.resume();

    audioQueue = [];
    offset = 0;
    playing = true;

    proc = ctx.createScriptProcessor(2048, 0, 1);
    proc.onaudioprocess = e => {
      const out = e.outputBuffer.getChannelData(0);
      out.fill(0);
      let pos = 0;

      while (pos < out.length && audioQueue.length) {
        const chunk = audioQueue[0];
        const n = Math.min(chunk.length - offset, out.length - pos);
        out.set(chunk.subarray(offset, offset + n), pos);
        pos += n;
        offset += n;
        if (offset >= chunk.length) {
          audioQueue.shift();
          offset = 0;
        }
      }
    };
    proc.connect(ctx.destination);

    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    ws = new WebSocket(proto + "//" + location.host + "/audio");
    ws.binaryType = "arraybuffer";

    ws.onmessage = e => {
      if (!playing) return;
      const view = new DataView(e.data);
      const a = new Float32Array(view.byteLength / 2);
      for (let i = 0; i < a.length; i++)
        a[i] = view.getInt16(i * 2, true) / 32768;

      audioQueue.push(a);
      while (audioQueue.length > 20) audioQueue.shift();
    };
    ws.onerror = () => $("status").textContent = "Audio socket error";
  } catch(e) {
    $("status").textContent = "Playback error: " + e.message;
    stop();
  }
};

function stop() {
  playing = false;
  if (ws) { ws.close(); ws = null; }
  if (proc) { proc.disconnect(); proc = null; }
  if (ctx) { ctx.close(); ctx = null; }
  audioQueue = [];
  offset = 0;
}

$("stop").onclick = stop;
window.addEventListener("beforeunload", stop);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    ensure_model()

    print("Loading Vosk model...")
    model = Model(str(MODEL_DIR))
    print("Model ready.")

    threading.Thread(
        target=udp_receiver, args=(model,), daemon=True
    ).start()

    threading.Thread(
        target=monitor, daemon=True
    ).start()

    print("Open http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=WEB_PORT,
        threaded=True,
        debug=False,
        use_reloader=False
    )
