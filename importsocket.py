import socket
import cv2
import numpy as np

# IP and port of warehouse PC streaming server
IP = '192.168.0.100'
PORT = 5002

# Connect to streaming server
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((IP, PORT))
print("Connected, requesting video...")

# ArUco setup
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
aruco_params = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

# Buffer to hold incoming data
buffer = b''

while True:
    sock.sendall(b'G 1')
    
    data = sock.recv(65535)
    if not data:
        print("Connection closed")
        break

    # Append received data to buffer
    buffer += data
    
    # Look for JPEG start and end markers
    start = buffer.find(b'\xff\xd8')
    end = buffer.find(b'\xff\xd9')

    # If we have a complete JPEG image, process it
    if start != -1 and end != -1:
        jpg = buffer[start:end+2]
        buffer = buffer[end+2:]

        # Decode JPEG to OpenCV image
        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            # Detect ArUco markers
            corners, ids, _ = detector.detectMarkers(frame)

            # If markers detected, calculate and print car position
            if ids is not None:
                cv2.aruco.drawDetectedMarkers(frame, corners, ids)

                # Assuming the car is represented by the first detected marker
                for i, corner in enumerate(corners):
                    cx = int(corner[0][:, 0].mean())
                    cy = int(corner[0][:, 1].mean())
                    print(f"Car position: ({cx}, {cy})")

                    # Draw position on frame
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    cv2.putText(frame, f"({cx},{cy})", (cx+10, cy),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                print("Car not detected")

            # Display the frame
            cv2.imshow('Overhead Camera', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        print("Quitting...")
        break

sock.close()
cv2.destroyAllWindows()