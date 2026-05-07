# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# This program allows the user to control a forklift robot using the arrow keys and W/S keys for the fork. 
# It sends commands to a Raspberry Pi over UDP to control the robot's movements.

import keyboard
import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Please enter PI_IP.")
PI_IP = input().strip()
PI_PORT = 4002

print("S = start | ESC = quit")

while True:
    if keyboard.is_pressed('esc'):
        sock.sendto(b'stop', (PI_IP, PI_PORT))
        break
    elif keyboard.is_pressed('w'):
        sock.sendto(b'start', (PI_IP, PI_PORT))
    else:
        sock.sendto(b'stop', (PI_IP, PI_PORT))

    time.sleep(0.02)