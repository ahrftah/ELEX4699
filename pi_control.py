# pi_control.py
# Implements the ELEX4699 forklift program on a Raspberry Pi 4.

# Import custom modules
import communication

def main():
    OVERHEAD_IP   = '192.168.0.100'
    OVERHEAD_PORT = 5002
    PC_IP = '192.168.137.1'
    PC_PORT      = 4002

    # Main Loop
    while True:
        
        #########################
        # STEP 1. END PROGRAM   #
        #########################
        pc_sock = communication.create_udp_socket(PC_IP,PC_PORT) # returns socket or None
        if pc_sock is None: # socket communication failed
            break
        
        command, addr = communication.receive_command(pc_sock)
        if command is not None:
            print(command)
            communication.send_command(pc_sock, command, PC_IP, PC_PORT)
        else:
            print('None')
        
        pc_sock.close()

        if command == 'quit':
            break

    #################
    # END PROGRAM   #
    #################

    print("Exiting main()")

if __name__ == "__main__":
    main()
    