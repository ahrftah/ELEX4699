# ELEX4699.py
# Authors: Bardia Jalali and Aiden Higginson
# Autonomous forklift controller. Press S to start, ESC to quit.

import keyboard
import socket
import cv2
import numpy as np
import math
import time

# ---- Network config ----
print("Enter Pi IP:")
PI_IP = input().strip()
MOTOR_PORT = 4002
DETECT_PORT = 4003
OVERHEAD_IP = '192.168.0.100'
OVERHEAD_PORT = 5002

# ---- Sockets ----
motor_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

detect_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
detect_sock.bind(('0.0.0.0', DETECT_PORT))
detect_sock.setblocking(False)

overhead_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
overhead_sock.connect((OVERHEAD_IP, OVERHEAD_PORT))

# ---- ArUco for car tracking (overhead camera) ----
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
detector = cv2.aruco.ArucoDetector(aruco_dict, cv2.aruco.DetectorParameters())

# ---- Waypoints ----
PICKUP_POINT  = (180, 180)   # near top wall
DELIVERY_ZONE = (190, 584)   # shelf delivery zone

# ---- Helpers ----
def send_motor(cmd):
    motor_sock.sendto(cmd.encode(), (PI_IP, MOTOR_PORT))
    time.sleep(0.02)

def get_overhead_frame():
    overhead_sock.sendall(b'G 1')
    buf = b''
    while True:
        buf += overhead_sock.recv(65535)
        if b'\xff\xd9' in buf:
            break
    s = buf.find(b'\xff\xd8')
    e = buf.find(b'\xff\xd9')
    if s != -1 and e != -1:
        jpg = buf[s:e+2]
        return cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
    return None

def get_car_pose(frame):
    """Returns (cx, cy), heading_angle or None, None if not found."""
    corners, ids, _ = detector.detectMarkers(frame)
    if ids is not None and len(corners) > 0:
        c = corners[0][0]
        cx = int(c[:, 0].mean())
        cy = int(c[:, 1].mean())
        top_mx = (c[0][0] + c[1][0]) / 2
        top_my = (c[0][1] + c[1][1]) / 2
        heading = math.atan2(top_my - cy, top_mx - cx)
        return (cx, cy), heading
    return None, None

def navigate_to(target, threshold=35):
    """Drive car to target pixel coordinate using overhead camera."""
    print(f"Navigating to {target}...")
    last_cmd = None

    while True:
        frame = get_overhead_frame()
        if frame is None:
            continue

        car_pos, heading = get_car_pose(frame)

        if car_pos is None:
            print("Car not visible, waiting...")
            send_motor('stop')
            time.sleep(0.1)
            continue

        cx, cy = car_pos
        tx, ty = target
        dist = math.sqrt((tx - cx)**2 + (ty - cy)**2)

        # Draw overlay
        cv2.circle(frame, car_pos, 8, (0, 255, 0), -1)
        cv2.putText(frame, "CAR", (cx + 10, cy), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        cv2.circle(frame, target, 8, (0, 0, 255), -1)
        cv2.putText(frame, "TARGET", (tx + 10, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        cv2.line(frame, car_pos, target, (255, 0, 0), 2)
        cv2.putText(frame, f"Dist: {dist:.0f}px", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imshow('Navigation', frame)

        if dist < threshold:
            send_motor('stop')
            print(f"Reached {target}!")
            break

        target_angle = math.atan2(ty - cy, tx - cx)
        angle_diff = target_angle - heading
        while angle_diff >  math.pi: angle_diff -= 2 * math.pi
        while angle_diff < -math.pi: angle_diff += 2 * math.pi

        if abs(angle_diff) > 0.35:
            cmd = 'right' if angle_diff > 0 else 'left'
        else:
            cmd = 'forward'

        if cmd != last_cmd:
            send_motor(cmd)
            last_cmd = cmd

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

        time.sleep(0.05)

def wait_for_package(timeout=20):
    """Block until Pi onboard camera reports a package."""
    print("Waiting for package detection...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            data, _ = detect_sock.recvfrom(1024)
            msg = data.decode().strip()
            if 'PACKAGE' in msg:
                print(f"Package found: {msg}")
                return msg
        except BlockingIOError:
            pass
        time.sleep(0.05)
    print("Timeout — no package detected.")
    return None

# ---- Main sequence ----
print("Press S to start autonomous mode. ESC to quit.")

while True:
    if keyboard.is_pressed('esc'):
        break

    if keyboard.is_pressed('s'):
        print("\n=== Autonomous sequence started ===")

        # 1. Navigate to pickup point near top wall
        navigate_to(PICKUP_POINT)
        time.sleep(0.5)

        # 2. Wait for onboard camera to detect package on wall
        pkg = wait_for_package()
        if pkg is None:
            print("No package found. Stopping.")
            send_motor('stop')
            break

        # 3. Pick up package
        print("Picking up package...")
        send_motor('fork_down')
        time.sleep(1.2)
        send_motor('forward')
        time.sleep(0.8)
        send_motor('stop')
        time.sleep(0.3)
        send_motor('fork_up')
        time.sleep(1.2)

        # 4. Reverse away from wall
        print("Reversing...")
        send_motor('backward')
        time.sleep(1.0)
        send_motor('stop')
        time.sleep(0.3)

        # 5. Turn around 180
        print("Turning around...")
        send_motor('right')
        time.sleep(2.0)
        send_motor('stop')
        time.sleep(0.3)

        # 6. Navigate to delivery zone
        navigate_to(DELIVERY_ZONE)
        time.sleep(0.5)

        # 7. Push package into shelf and back up
        print("Delivering package...")
        send_motor('forward')
        time.sleep(0.6)
        send_motor('stop')
        time.sleep(0.3)
        send_motor('fork_down')
        time.sleep(1.0)
        send_motor('backward')
        time.sleep(1.0)
        send_motor('stop')

        print("=== Delivery complete! ===")
        break

    time.sleep(0.02)

cv2.destroyAllWindows()
