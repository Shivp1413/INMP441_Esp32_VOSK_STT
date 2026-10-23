import socket

rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
rx.bind(("192.168.4.2", 3333))

tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Relay: waiting for ESP32 audio")

while True:
    data, addr = rx.recvfrom(65535)
    if addr[0] == "192.168.4.1":
        tx.sendto(data, ("192.168.137.96", 3333))
