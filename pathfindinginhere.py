import socket
import cv2
import numpy as np
from skimage.graph import route_through_array

# Global variable to store clicked destination
goal_pos = (50, 50)

def handle_click(event, x, y, flags, param):
    global goal_pos
    if event == cv2.EVENT_LBUTTONDOWN:
        goal_pos = (x, y)
        print(f"New Goal Set: {goal_pos}")

def warehouse_communication():
    global goal_pos
    IP = '192.168.0.100'
    PORT = 5002

    # Connect to streaming server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((IP, PORT))
        # Set a timeout so the script doesn't hang forever if the stream drops
        sock.settimeout(2.0)
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    # Setup window and mouse callback
    cv2.namedWindow('Live Feed')
    cv2.setMouseCallback('Live Feed', handle_click)

    buffer = b''

    try:
        while True:
            # Request frame
            sock.sendall(b'G 1')
            try:
                data = sock.recv(65535)
            except socket.timeout:
                continue
                
            if not data: break

            buffer += data
            start = buffer.find(b'\xff\xd8')
            end = buffer.find(b'\xff\xd9')

            if start != -1 and end != -1:
                jpg = buffer[start:end+2]
                buffer = buffer[end+2:]
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)

                if frame is not None:
                    h, w = frame.shape[:2]
                    
                    # --- 1. DEFINE OBSTACLES ---
                    binary_obstacles = np.zeros((h, w), dtype=np.uint8)
                    cv2.rectangle(binary_obstacles, (0, 0), (w-1, h-1), 255, 3) # Boundary
                    cv2.rectangle(binary_obstacles, (110, 440), (130, 585), 255, -1)
                    cv2.rectangle(binary_obstacles, (480, 480), (495, 595), 255, -1)
                    cv2.rectangle(binary_obstacles, (270, 220), (330, 240), 255, -1)

                    # --- 2. PREPARE COST MAP ---
                    cost_map = np.ones((h, w), dtype=np.float32)
                    kernel = np.ones((15, 15), np.uint8) 
                    buffered_obstacles = cv2.dilate(binary_obstacles, kernel, iterations=1)
                    cost_map[buffered_obstacles == 255] = 1000000.0

                    # --- 3. DETECTION & PATHFINDING ---
                    corners, ids, _ = detector.detectMarkers(frame)

                    if ids is not None and len(ids) > 0:
                        cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                        # Center of the first detected marker
                        cx, cy = int(corners[0][0][:, 0].mean()), int(corners[0][0][:, 1].mean())
                        tx, ty = goal_pos

                        try:
                            # skimage uses (row, col) -> (y, x)
                            path, _ = route_through_array(cost_map, (cy, cx), (ty, tx))
                            
                            # Draw the path onto the live frame
                            for coord in path:
                                # coord is (y, x), cv2.circle needs (x, y)
                                frame[coord[0], coord[1]] = [0, 255, 0] 
                        
                        except Exception:
                            cv2.putText(frame, "NO PATH", (50, 50), 
                                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                    # --- 4. DISPLAY FEED ---
                    cv2.imshow('Live Feed', frame)
                    
                    # Essential: waitKey(1) processes GUI events and prevents crashing
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
    finally:
        sock.close()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    warehouse_communication()