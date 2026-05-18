# pi_control.py
import communication
import motors
import time

def main():
    OVERHEAD_IP   = '192.168.0.100'
    OVERHEAD_PORT = 5002
    PC_IP   = '192.168.137.1'
    PC_PORT = 4002
    PC_VIDEO_PORT = 5002

    state = 'MANUAL'
    # ... (Keep your movements dictionary mapping unchanged)

    pc_sock = communication.create_udp_socket('0.0.0.0', PC_PORT)
    if pc_sock is None: 
        return

    # Connect to the overhead camera environment
    overhead_sock = communication.connect_to_overhead(OVERHEAD_IP, OVERHEAD_PORT)
    
    # Connect back to the PC client to stream video frames
    print("Connecting to PC video server...")
    video_sock = communication.connect_to_overhead(PC_IP, PC_VIDEO_PORT)

    while True:
        # STEP 1. GET COMMAND
        command, addr = communication.receive_command(pc_sock, 0.1)
        if command is not None:
            print(command)
            communication.send_command(pc_sock, command, PC_IP, PC_PORT)  

        if command == 'quit':
            break
        if command == 'manual':
            state = 'MANUAL'

        # STEP 2. STATE MACHINE LOOP
        if state == 'MANUAL':
            # ... (your existing manual motor parsing blocks)
            pass
            
        elif state == 'AUTO_IDLE':
            if command == 'start':
                state = 'PATHFIND_TO_PICKUP'
                
        elif state == 'PATHFIND_TO_PICKUP':
            # 1. Grab a frame from the overhead camera server
            if overhead_sock:
                frame = communication.get_overhead_frame(overhead_sock)
                
                if frame is not None:
                    # 2. Stream that image live right over to the user's computer screen!
                    if video_sock:
                        communication.send_frame_tcp(video_sock, frame)
                    
                    # 3. Proceed with your pathfinding marker processing logic here...

    pc_sock.close()
    if overhead_sock: overhead_sock.close()
    if video_sock: video_sock.close()
    print("Exiting main()")

if __name__ == "__main__":
    main()