# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# PC client — press G to start autonomous mode, ESC to quit.

import keyboard
import communication
import time

def main():
    print("Enter Pi IP:")
    PI_IP = input().strip()
    PI_PORT = 4002


    userexit = False
    while userexit == False:
        pi_sock = communication.create_udp_socket('0.0.0.0',PI_PORT)
        if pi_sock is None: # socket communication failed
            break

        print("ESC = quit")

        # Loop until user exits.
        while userexit == False:
            command = None
            if keyboard.is_pressed('esc'):
                command = 'quit'
                userexit = True
            elif keyboard.is_pressed('up'):
                command = 'forward'
            elif keyboard.is_pressed('down'):
                command = 'backward'
            elif keyboard.is_pressed('left'):
                command = 'left'
            elif keyboard.is_pressed('right'):
                command = 'right'
            elif keyboard.is_pressed('m'):
                command = 'manual'
            elif keyboard.is_pressed('a'):
                command = 'automatic'
            elif keyboard.is_pressed('s'):
                command = 'start'
            if command is not None:
                communication.send_command(pi_sock, command, PI_IP, PI_PORT)
            time.sleep(0.02)
        pi_sock.close()

if __name__ == "__main__":
    main()