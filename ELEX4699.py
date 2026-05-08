# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# PC client — press G to start autonomous mode, ESC to quit.

import keyboard
import socket
import time

print("Enter Pi IP:")
PI_IP = input().strip()
PI_PORT = 4002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("G = start autonomous | ESC = quit")

start_sent = False

while True:
    if keyboard.is_pressed('esc'):
        sock.sendto(b'stop', (PI_IP, PI_PORT))
        break
    elif keyboard.is_pressed('g') and start_sent is False:
        sock.sendto(b'start', (PI_IP, PI_PORT))
        print("Start command sent!")
        start_sent = True

    time.sleep(0.02)
