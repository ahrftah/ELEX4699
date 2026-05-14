import socket
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# PC <-> Pi : UDP command channel
# ---------------------------------------------------------------------------

def create_udp_socket(ip, port):
    """
    Bind a UDP socket to (ip, port).
    Use on whichever side needs to receive (both sides can share one socket
    for send/receive since UDP is connectionless).
    Returns the socket, or None on failure.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind((ip, port))
        print(f"UDP socket bound to {ip}:{port}")
        return s
    except Exception as e:
        print(f"Error creating UDP socket on {ip}:{port} — {e}")
    return None


def send_command(sock, message, target_ip, target_port):
    """Send a short UTF-8 command string to (target_ip, target_port) via UDP."""
    try:
        sock.sendto(message.encode(), (target_ip, target_port))
    except Exception as e:
        print(f"Error sending command: {e}")


def receive_command(sock, timeout=3.0, buffer_size=1024):
    """
    Block until a UDP command arrives.
    Returns (command_string, sender_addr), or (None, None) on error/timeout.
    sender_addr is a (ip, port) tuple — useful for replying back.
    """
    sock.settimeout(timeout)
    try:
        data, addr = sock.recvfrom(buffer_size)
        if not data:
            return None, None
        return data.decode().strip(), addr
    except TimeoutError:
        return None, None
    except Exception as e:
        print(f"Error receiving command: {e}")
        return None, None


# ---------------------------------------------------------------------------
# Pi <-> Overhead camera : TCP image channel
# ---------------------------------------------------------------------------

def connect_to_overhead(ip, port):
    """
    Open a TCP connection to the overhead camera server.
    Returns the socket, or None on failure.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        print(f"Connected to overhead camera at {ip}:{port}")
        return s
    except Exception as e:
        print(f"Error connecting to overhead camera at {ip}:{port} — {e}")
    return None


def get_overhead_frame(sock, timeout=5.0):
    """
    Request a JPEG frame from the overhead camera.
    Sends 'G 1', then reads until the JPEG end-of-image marker is found.
    Returns a decoded OpenCV BGR frame, or None on failure.
    """
    sock.sendall(b'G 1')
    buf = b''

    sock.settimeout(timeout)

    try:
        while True:
            chunk = sock.recv(65535)
            if not chunk:
                break
            buf += chunk
            if b'\xff\xd9' in buf:      # JPEG End of Image marker
                break
    except socket.timeout:
        print("Error: Timed out waiting for frame from overhead camera.")
        return None

    start = buf.find(b'\xff\xd8')       # JPEG Start of Image marker
    end   = buf.find(b'\xff\xd9')

    if start != -1 and end != -1:
        jpg = buf[start:end + 2]
        print(f"Received JPEG frame: {len(jpg)} bytes")
        frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is not None:
            return frame

    print("Error: Could not decode JPEG frame from overhead camera.")
    return None


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os
    import threading

    OVERHEAD_IP   = '192.168.0.100'
    OVERHEAD_PORT = 5002
    UDP_LISTEN_IP = '0.0.0.0'
    UDP_PORT      = 4002

    # --- Test 1: UDP loopback (send a command to ourselves) ---
    print("\n=== Test 1: UDP loopback ===")
    receiver = create_udp_socket(UDP_LISTEN_IP, UDP_PORT)
    if receiver:
        receiver.settimeout(3.0)

        # Send a command from a temporary socket to our own receiver
        def _send():
            tmp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            tmp.sendto(b'PING', ('127.0.0.1', UDP_PORT))
            tmp.close()

        threading.Thread(target=_send, daemon=True).start()

        command, addr = receive_command(receiver)
        if command == 'PING':
            print(f"UDP loopback OK — received '{command}' from {addr}")
            send_command(receiver, 'PONG', *addr)
            print("UDP send_command OK — sent 'PONG' back")
        else:
            print(f"UDP loopback FAILED — got: {command}")
        receiver.close()
    else:
        print("UDP loopback FAILED — could not create socket")

    # --- Test 2: TCP connection + frame grab from overhead camera ---
    print("\n=== Test 2: Overhead camera frame grab ===")
    cam_sock = connect_to_overhead(OVERHEAD_IP, OVERHEAD_PORT)
    if cam_sock:
        frame = get_overhead_frame(cam_sock)
        if frame is not None:
            h, w, _ = frame.shape
            out = "overhead_test.jpg"
            cv2.imwrite(out, frame)
            print(f"Frame grab OK — {w}x{h}, saved to {os.path.abspath(out)}")
        else:
            print("Frame grab FAILED — no frame returned")
        cam_sock.close()
    else:
        print("Frame grab FAILED — could not connect to overhead camera")
