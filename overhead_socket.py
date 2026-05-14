import socket
import cv2
import numpy as np  # Needed for imdecode
import os

OVERHEAD_IP   = '192.168.0.100'
OVERHEAD_PORT = 5002

def connect_socket(ip, port):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        return s
    except Exception as e:
        print(f"Error connecting to overhead camera: {e}")
    return None
    

def get_overhead_frame(s):
    s.sendall(b'G 1')
    buf = b''
    
    # We add a timeout so the script doesn't hang forever if the camera fails
    s.settimeout(5.0) 
    
    try:
        while True:
            chunk = s.recv(65535)
            if not chunk: break
            buf += chunk
            if b'\xff\xd9' in buf: # JPEG End of Image marker
                break
    except socket.timeout:
        print("Error: Socket timed out waiting for data.")
        return None

    start = buf.find(b'\xff\xd8') # JPEG Start of Image marker
    end   = buf.find(b'\xff\xd9')
    
    if start != -1 and end != -1:
        jpg = buf[start:end+2]
        # Check raw byte size
        print(f"Raw data received: {len(jpg)} bytes")
        
        # Decode the image
        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        if frame is not None:
            # Confirm frame dimensions
            h, w, c = frame.shape
            return frame
    return None

if __name__ == "__main__":
    try:
        sock = connect_socket(OVERHEAD_IP, OVERHEAD_PORT)
        img = get_overhead_frame(sock)
        
        if img is not None:
            # Save to disk so you can download/inspect it later
            filename = "capture_test.jpg"
            cv2.imwrite(filename, img)
            print(f"Verification image saved as: {os.path.abspath(filename)}")
        else:
            print("Failed to capture image.")
            
        sock.close()
    except Exception as e:
        print(f"Connection Error: {e}")