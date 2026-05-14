# pi_control.py
# Implements the ELEX4699 forklift program on a Raspberry Pi 4.

# Import custom modules
import communication
import motors

def main():
    OVERHEAD_IP   = '192.168.0.100'
    OVERHEAD_PORT = 5002
    PC_IP = '192.168.137.1'
    PC_PORT      = 4002

    state = 'MANUAL'
    movements = {
        'forward':motors.forward,
        'backward':motors.backward,
        'left':motors.left,
        'right':motors.right,
        'stop':motors.stop
    }

    pc_sock = communication.create_udp_socket('0.0.0.0',PC_PORT) # returns socket or None
    if pc_sock is None: # socket communication failed
        return

    # Main Loop
    while True:
        
        #########################
        # STEP 1. GET COMMAND   #
        #########################
        command, addr = communication.receive_command(pc_sock, 0.1)
        if command is not None:
            print(command)
            communication.send_command(pc_sock, command, PC_IP, PC_PORT)  

        if command == 'quit':
            break
        
        if command == 'manual':
            state = 'MANUAL'

        #####################################################
        # STEP 2. ENTER STATE FUNCTION. INTERPRET COMMAND   #
        #####################################################

        if state == 'MANUAL':
            print(state)
            if command == 'automatic':
                # change of state
                motors.stop()
                state = 'AUTO_IDLE'
            else:
                try:
                    movements[command]()
                except KeyError:
                    motors.stop()
        elif state == 'AUTO_IDLE':
            print(state)
            if command == 'start':
                state = 'PATHFIND_TO_PICKUP'
        elif state == 'PATHFIND_TO_PICKUP':
            print(state)


    #################
    # END PROGRAM   #
    #################
    pc_sock.close()
    print("Exiting main()")

if __name__ == "__main__":
    main()
    