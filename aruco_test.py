import cv2
import time
import overhead_socket

# --- Configuration ---
MOTOR_PORT    = 4002
OVERHEAD_IP   = '192.168.0.100'
OVERHEAD_PORT = 5002

PICKUP_POINT  = (180, 180)
DELIVERY_ZONE = (190, 584)

def run_camera_stream():
    sock = None
    print(f"Connecting to overhead camera at {OVERHEAD_IP}...")

    try:
        while True:
            # Establish connection if it doesn't exist
            if sock is None:
                sock = overhead_socket.connect_socket(OVERHEAD_IP, OVERHEAD_PORT)
                if sock is None:
                    print("Connection failed. Retrying in 5s...")
                    time.sleep(5)
                    continue
                print("Connected!")

            # Capture frame
            img = overhead_socket.get_overhead_frame(sock)
            
            if img is not None:
                cv2.imshow("Overhead View", img)
            else:
                print("Dropped frame or lost connection.")
                sock.close()
                sock = None  # Trigger a reconnect in the next loop

            # Break loop on 'q' press (1ms delay for snappy video)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nStopping stream...")
    except Exception as e:
        print(f"Unexpected Error: {e}")
    finally:
        # Cleanup resources
        if sock:
            sock.close()
        cv2.destroyAllWindows()
        print("Resources released.")

if __name__ == "__main__":
    run_camera_stream()