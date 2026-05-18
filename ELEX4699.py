# ELEX4699.py
import keyboard
import communication
import time
import socket
import threading
import cv2

def video_stream_worker(video_sock):
    """Background thread function that receives and renders images without lagging controls."""
    print("Video stream worker thread initialized.")
    try:
        while True:
            frame = communication.receive_frame_tcp(video_sock)
            if frame is not None:
                cv2.imshow("Raspberry Pi Video Feed", frame)
                # cv2.waitKey(1) pumps GUI events; required for imshow windows to paint properly
                if cv2.waitKey(1) & 0xFF == 27:  
                    break
            else:
                time.sleep(0.01)  # Yield CPU if no new frame arrived
    finally:
        cv2.destroyAllWindows()
        print("Video display window closed.")

def main():
    print("Enter Pi IP:")
    PI_IP = input().strip()
    PI_PORT = 4002
    VIDEO_PORT = 5002

    # 1. Setup UDP command socket
    pi_sock = communication.create_udp_socket('0.0.0.0', PI_PORT)
    if pi_sock is None:
        print("Socket communication failed to initialize.")
        return

    # 2. Setup TCP Server Socket to accept video stream from the Pi
    video_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_server.bind(('0.0.0.0', VIDEO_PORT))
    video_server.listen(1)
    print(f"TCP Video Server listening on port {VIDEO_PORT}... Boot up the Pi script now.")
    
    # Blocks here until your Pi runs and connects to the PC
    video_sock, addr = video_server.accept()
    print(f"Connected to Pi video stream from {addr}")

    # 3. Spin up the background image processor thread
    video_thread = threading.Thread(target=video_stream_worker, args=(video_sock,), daemon=True)
    video_thread.start()

    KEY_MAP = {
        'esc': 'quit', 'up': 'forward', 'down': 'backward', 
        'left': 'left', 'right': 'right', 'e': 'fork_up', 
        'q': 'fork_down', 'm': 'manual', 'a': 'automatic', 's': 'start'
    }

    print("Control mode active. ESC = quit")
    TICK_RATE = 0.05

    try:
        while True:
            active_command = None
            for key, command in KEY_MAP.items():
                if keyboard.is_pressed(key):
                    active_command = command
                    break

            if active_command:
                communication.send_command(pi_sock, active_command, PI_IP, PI_PORT)
                if active_command == 'quit':
                    break

            time.sleep(TICK_RATE)
    finally:
        pi_sock.close()
        video_sock.close()
        video_server.close()
        print("Sockets closed successfully.")

if __name__ == "__main__":
    main()