# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# PC client — press G to start autonomous mode, ESC to quit.

import keyboard
import communication

def main():
    print("Enter Pi IP:")
    PI_IP = input().strip()
    PI_PORT = 4002

    # Open the socket once up front instead of nesting it in redundant loops
    pi_sock = communication.create_udp_socket('0.0.0.0', PI_PORT)
    if pi_sock is None:
        print("Socket communication failed to initialize.")
        return

    # Dictionary lookup is cleaner and faster than a long if-elif chain
    KEY_MAP = {
        'esc': 'quit',
        'up': 'forward',
        'down': 'backward',
        'left': 'left',
        'right': 'right',
        'm': 'manual',
        'a': 'automatic',
        's': 'start'
    }

    print("Control mode active. ESC = quit")

    try:
        while True:
            # Blocks the loop and waits until a key is pressed or released
            event = keyboard.read_event()

            # Only trigger on the initial press down, ignoring the key release
            if event.event_type == keyboard.KEY_DOWN:
                command = KEY_MAP.get(event.name)
                
                if command:
                    communication.send_command(pi_sock, command, PI_IP, PI_PORT)
                    
                    if command == 'quit':
                        break
    finally:
        # Ensures the socket always closes cleanly when exiting
        pi_sock.close()
        print("Socket closed successfully.")

if __name__ == "__main__":
    main()