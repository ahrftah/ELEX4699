# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# This program allows the user to control a forklift robot using the arrow keys and W/S keys for the fork. 
# It sends commands to a Raspberry Pi over UDP to control the robot's movements.

import keyboard
import socket
import time

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
PI_IP = 'higginson'
PI_PORT = 4002

print("Arrow keys = drive | W = fork up | S = fork down | ESC = quit")

while True:
    if keyboard.is_pressed('esc'):
        sock.sendto(b'stop', (PI_IP, PI_PORT))
        break
    elif keyboard.is_pressed('up'):
        sock.sendto(b'forward', (PI_IP, PI_PORT))
    elif keyboard.is_pressed('down'):
        sock.sendto(b'backward', (PI_IP, PI_PORT))
    elif keyboard.is_pressed('left'):
        sock.sendto(b'left', (PI_IP, PI_PORT))
    elif keyboard.is_pressed('right'):
        sock.sendto(b'right', (PI_IP, PI_PORT))
    elif keyboard.is_pressed('w'):
        sock.sendto(b'fork_up', (PI_IP, PI_PORT))
    elif keyboard.is_pressed('s'):
        sock.sendto(b'fork_down', (PI_IP, PI_PORT))
    else:
        sock.sendto(b'stop', (PI_IP, PI_PORT))

    time.sleep(0.02)