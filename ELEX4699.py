# ELEX4699.py
import keyboard
import communication
import time
import socket
import threading
import cv2

def video_stream_worker(video_sock):
    """Background thread function that receives and renders images."""
    print("Video stream worker thread initialized.")
    try:
        while True:
            frame = communication.receive_frame_tcp(video_sock, timeout=2.0)
            if frame is not None:
                print("valid frame")
                cv2.imshow("Raspberry Pi Video Feed", frame)
                if cv2.waitKey(1) & 0xFF == 27:  
                    break
            else:
                time.sleep(0.01)
    except (OSError, ConnectionAbortedError):
        # This catches WinError 10038 cleanly when the main thread shuts down the socket.
        # We absorb it and exit the thread silently since it means we are closing down anyway.
        pass
    except Exception as e:
        print(f"Unexpected error in video thread: {e}")
    finally:
        cv2.destroyAllWindows()

def main():
    print("Enter Pi IP:")
    PI_IP = input().strip()
    PI_PORT = 4002
    VIDEO_PORT = 5002  # Keeping it on your specifications port

    # 1. Setup UDP command socket
    pi_sock = communication.create_udp_socket('0.0.0.0', PI_PORT)
    if pi_sock is None:
        print("Socket communication failed to initialize.")
        return

    # 2. Setup TCP Server Socket for video on port 5002
    video_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    video_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    video_server.bind(('0.0.0.0', VIDEO_PORT))
    video_server.listen(1)
    print(f"TCP Video Server listening on port {VIDEO_PORT}... Boot up the Pi script now.")
    
    video_sock, addr = video_server.accept()
    print(f"Connected to Pi video stream from {addr}")

    # 3. Spin up the background image processor thread
    video_thread = threading.Thread(target=video_stream_worker, args=(video_sock,), daemon=True)
    video_thread.start()

    KEY_MAP = {
        'esc': 'quit', 
        'up': 'forward', 
        'down': 'backward', 
        'left': 'left', 
        'right': 'right', 
        'e': 'fork_up', 
        'q': 'fork_down', 
        'm': 'manual', 
        'a': 'automatic', 
        's': 'start'
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
        # Closes sockets immediately when 'esc' drops out of the while loop
        pi_sock.close()
        video_sock.close()
        video_server.close()
        print("Sockets closed successfully. Goodbye!")

if __name__ == "__main__":
    main()