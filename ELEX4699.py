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
            if keyboard.is_pressed('esc'):
                communication.send_command(pi_sock, 'quit', PI_IP, PI_PORT)
                print(communication.receive_command(pi_sock))
                userexit = True
            time.sleep(0.02)
        pi_sock.close()

if __name__ == "__main__":
    main()