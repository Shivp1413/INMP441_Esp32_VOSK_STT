# INMP441 ESP32 Audio — Live Speech-to-Text (STT)

Real-time English **Speech-to-Text (STT)** using an ESP32-S3, INMP441 I2S microphone, UDP audio streaming, and Vosk speech recognition.

The main goal of this project is to convert live microphone audio into text and display the transcription in a real-time web dashboard.

<p align="center">
  <img src="https://github.com/Shivp1413/INMP441_Esp32_VOSK_STT/blob/main/assets/Capture.PNG" width="820" />
  <img src="https://github.com/Shivp1413/INMP441_Esp32_VOSK_STT/blob/main/assets/Capture2.PNG" width="820" />
</p>


<table>
<tr>
<td align="center" width="50%">
<img width="660" height="1280" alt="esp32s3" src="https://github.com/user-attachments/assets/2d37504d-cc0c-4cc1-b8d7-22a594ad3d33" />
<b>ESP32-S3 Development Board</b>
</td>

<td align="center" width="50%">
<img width="992" height="1280" alt="mic" src="https://github.com/user-attachments/assets/d35464f4-9198-4abe-9450-8345e3f8217f" />
<b>INMP441 I2S MEMS Microphone</b>
</td>
</tr>
</table>

## ✨ Features

- 🎙️ Real-time English Speech-to-Text (STT)
- 🧠 Offline speech recognition using Vosk
- 📡 Live audio streaming over UDP
- 📝 Live and finalized transcription
- 🎧 Browser-based audio playback
- 📊 Real-time audio level monitoring
- 💻 CPU and memory usage monitoring
- 🌐 Web dashboard with live updates
- 🔊 16 kHz, 16-bit mono PCM audio
- 🔌 ESP32-S3 with INMP441 I2S microphone

## 🛠️ Hardware Requirements

- ESP32-S3 development board
- INMP441 I2S microphone
- USB cable

## 🔌 Wiring

| INMP441 Microphone | ESP32-S3 |
|:---|:---|
| SCK / BCLK | GPIO 5 |
| WS / LRCL | GPIO 6 |
| SD | GPIO 4 |
| VDD | 3.3V |
| GND | GND |
| L/R | GND (left channel) |

> **Note:** Check your specific ESP32-S3 board's pin availability before wiring.

## 💻 Software Requirements

- Arduino IDE
- ESP32 Arduino core
- Python 3
- Vosk
- Flask
- Flask-Sock
- psutil

## 🚀 Getting Started

### 1. Upload the ESP32 Firmware

Upload the Arduino audio-streaming firmware to your ESP32-S3 and connect the INMP441 microphone according to the wiring table.

The ESP32 captures microphone audio and streams it over UDP on port `3333`.

Use the firmware.txt in Arduino IDE and flash your Esp32 module.

### 2. Install Python Dependencies

Install the required Python packages:

```bash
pip install vosk flask flask-sock psutil
```

### 3. Start the STT Server

Save the Python server code as `server.py` and run:

```bash
python main.py
```

The Vosk English speech recognition model is downloaded automatically on the first run.

### 4. Open the Web Dashboard

Open your browser and navigate to:

**http://127.0.0.1:5000**

Connect your computer to the ESP32 Wi-Fi network if access point mode is enabled.

Speak into the microphone to see the live English transcription on the dashboard.

Click **Play audio** to listen to the incoming microphone stream.

## 🧠 Speech-to-Text (STT)

**Speech-to-Text is the main feature of this project.**

The system uses Vosk for real-time English speech recognition. Spoken words are converted into text and displayed on the web dashboard.

- **Live transcription:** Displays partial recognition results as you speak.
- **Final transcription:** Displays completed recognized phrases.
- **Recent phrases:** Keeps a history of recent transcribed speech.
- **Offline recognition:** Speech recognition runs locally after the model has been downloaded.

Internet access is required for the initial model download. Once the model is installed, speech recognition can operate offline.

## 📊 Technical Specifications

| Parameter | Value |
|:---|:---|
| Microcontroller | ESP32-S3 |
| Microphone | INMP441 I2S |
| Sample rate | 16,000 Hz |
| Audio format | Signed 16-bit PCM |
| Audio channels | Mono |
| Audio transport | UDP |
| UDP port | `3333` |
| Web framework | Flask |
| Web dashboard port | `5000` |
| STT engine | Vosk |
| Recognition language | English |
| Speaker identification | Not enabled |

## 🔧 Troubleshooting

- **No transcription:** Check the microphone wiring and confirm that UDP audio packets reach the computer.
- **Dashboard not opening:** Make sure the Python server is running and port `5000` is accessible.
- **No audio playback:** Click **Play audio** and check your browser's audio support.
- **Poor transcription accuracy:** Reduce background noise and check the microphone signal level.
- **Model download problems:** Check your internet connection and restart the server.
- **ESP32 connection problems:** Ensure the ESP32 sends UDP packets to the receiving computer's correct IP address.

## 📂 Repository

GitHub: https://github.com/Shivp1413/INMP441_Esp32_VOSK_STT

## 📄 License

This project is released under the **MIT License**.

See the [`LICENSE`](LICENSE) file for details.
