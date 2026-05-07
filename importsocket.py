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

    while True:
        sock.sendall(b'G 1')
        data = sock.recv(65535)
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
                
                # Boundary wall
                cv2.rectangle(binary_obstacles, (0, 0), (w-1, h-1), 255, 3)
                # Obstacles from your snippet
                cv2.rectangle(binary_obstacles, (110, 440), (130, 585), 255, -1)
                cv2.rectangle(binary_obstacles, (480, 480), (495, 595), 255, -1)
                cv2.rectangle(binary_obstacles, (270, 220), (330, 240), 255, -1)

                # --- 2. PREPARE COST MAP ---
                # Start with a cost of 1 for empty space
                cost_map = np.ones((h, w), dtype=np.float32)
                
                # Add a "safety buffer" so the car doesn't hit the wall corners
                kernel = np.ones((15, 15), np.uint8) 
                buffered_obstacles = cv2.dilate(binary_obstacles, kernel, iterations=1)
                
                # Set obstacle costs to a very high number
                cost_map[buffered_obstacles == 255] = 1000000.0

                # --- 3. DETECTION & PATHFINDING ---
                path_map = np.zeros((h, w), dtype=np.uint8)
                corners, ids, _ = detector.detectMarkers(frame)

                if ids is not None:
                    cv2.aruco.drawDetectedMarkers(frame, corners, ids)
                    cx, cy = int(corners[0][0][:, 0].mean()), int(corners[0][0][:, 1].mean())
                    
                    # Target from mouse click
                    tx, ty = goal_pos

                    try:
                        # skimage uses (row, col) -> (y, x)
                        path, _ = route_through_array(cost_map, (cy, cx), (ty, tx))
                        
                        # Draw the path
                        for coord in path:
                            path_map[coord[0], coord[1]] = 255
                        path_map = cv2.dilate(path_map, np.ones((3,3), np.uint8))
                    except Exception as e:
                        print("No valid path found (Target might be inside a wall!)")

    return frame, binary_obstacles, path_map

    sock.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    warehouse_communication()