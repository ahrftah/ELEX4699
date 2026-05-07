# control.py
# Authors: Bardia Jalali and Aiden Higginson
# Runs on Raspberry Pi. Handles motors, navigation, and package detection.

from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
from multiprocessing import Process
import socket
import threading
import numpy as np
import math
import time

MOTOR_PORT  = 4002
CAMERA_PORT = 5000

OVERHEAD_IP   = '192.168.0.100'  # replace with overhead camera IP
OVERHEAD_PORT = 5002              # replace with overhead camera port

PICKUP_POINT  = (180, 180)
DELIVERY_ZONE = (190, 584)

def motor_server():
    import socket
    import time

    # ---- ArUco for car tracking ----
    car_aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    car_detector   = cv2.aruco.ArucoDetector(car_aruco_dict, cv2.aruco.DetectorParameters())

    # ---- ArUco for package detection ----
    pkg_aruco_dict   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    pkg_aruco_params = cv2.aruco.DetectorParameters()
    pkg_aruco_params.adaptiveThreshWinSizeMin = 3
    pkg_aruco_params.adaptiveThreshWinSizeMax = 23
    pkg_aruco_params.adaptiveThreshConstant   = 7
    pkg_aruco_params.minMarkerPerimeterRate    = 0.01
    pkg_detector = cv2.aruco.ArucoDetector(pkg_aruco_dict, pkg_aruco_params)

    # ---- GPIO setup ----
    AIN1, AIN2, PWMA = 4, 17, 18
    BIN1, BIN2, PWMB = 22, 27, 23
    SERVO_PIN = 24

    GPIO.setmode(GPIO.BCM)
    GPIO.setup([AIN1, AIN2, BIN1, BIN2], GPIO.OUT)
    GPIO.setup([PWMA, PWMB], GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    pwm_a = GPIO.PWM(PWMA, 1000)
    pwm_b = GPIO.PWM(PWMB, 1000)
    pwm_a.start(0)
    pwm_b.start(0)

    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)

    # ---- Motor helpers ----
    def set_motors(ain1, ain2, bin1, bin2, speed=100):
        GPIO.output(AIN1, ain1)
        GPIO.output(AIN2, ain2)
        GPIO.output(BIN1, bin1)
        GPIO.output(BIN2, bin2)
        pwm_a.ChangeDutyCycle(speed)
        pwm_b.ChangeDutyCycle(speed)

    def set_angle(angle):
        duty = 2.5 + (angle / 180) * 10
        servo.ChangeDutyCycle(duty)
        time.sleep(0.5)
        servo.ChangeDutyCycle(0)

    def forward():   set_motors(1, 0, 1, 0, 60)
    def backward():  set_motors(0, 1, 0, 1, 60)
    def left():      set_motors(0, 1, 1, 0, 30)
    def right():     set_motors(1, 0, 0, 1, 30)
    def stop():      set_motors(0, 0, 0, 0, 0)
    def fork_up():   set_angle(0)
    def fork_down(): set_angle(20)

    # ---- Overhead camera ----
    def connect_overhead():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((OVERHEAD_IP, OVERHEAD_PORT))
        return s

    def get_overhead_frame(s):
        s.sendall(b'G 1')
        buf = b''
        while True:
            buf += s.recv(65535)
            if b'\xff\xd9' in buf:
                break
        start = buf.find(b'\xff\xd8')
        end   = buf.find(b'\xff\xd9')
        if start != -1 and end != -1:
            jpg = buf[start:end+2]
            return cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        return None

    def get_car_pose(frame):
        corners, ids, _ = car_detector.detectMarkers(frame)
        if ids is not None and len(corners) > 0:
            c  = corners[0][0]
            cx = int(c[:, 0].mean())
            cy = int(c[:, 1].mean())
            top_mx  = (c[0][0] + c[1][0]) / 2
            top_my  = (c[0][1] + c[1][1]) / 2
            heading = math.atan2(top_my - cy, top_mx - cx)
            return (cx, cy), heading
        return None, None

    def navigate_to(overhead_sock, target, threshold=35):
        print(f"Navigating to {target}...")
        last_cmd = None
        while True:
            frame = get_overhead_frame(overhead_sock)
            if frame is None:
                continue

            car_pos, heading = get_car_pose(frame)
            if car_pos is None:
                print("Car not visible...")
                stop()
                time.sleep(0.1)
                continue

            cx, cy = car_pos
            tx, ty = target
            dist = math.sqrt((tx - cx)**2 + (ty - cy)**2)

            if dist < threshold:
                stop()
                print(f"Reached {target}!")
                return

            target_angle = math.atan2(ty - cy, tx - cx)
            angle_diff   = target_angle - heading
            while angle_diff >  math.pi: angle_diff -= 2 * math.pi
            while angle_diff < -math.pi: angle_diff += 2 * math.pi

            if abs(angle_diff) > 0.35:
                cmd = 'right' if angle_diff > 0 else 'left'
            else:
                cmd = 'forward'

            if cmd != last_cmd:
                if   cmd == 'forward': forward()
                elif cmd == 'right':   right()
                elif cmd == 'left':    left()
                last_cmd = cmd

            time.sleep(0.05)

    # ---- Onboard camera package scan ----
    def scan_for_package(timeout=20):
        print("Scanning for package...")
        cam = cv2.VideoCapture(0)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        deadline = time.time() + timeout
        found = None
        while time.time() < deadline:
            success, frame = cam.read()
            if not success:
                continue
            corners, ids, _ = pkg_detector.detectMarkers(frame)
            if ids is not None:
                for id in ids:
                    if id[0] in [38, 62]:
                        found = id[0]
                        print(f"Package detected: ID {found}")
                        break
            if found:
                break
            time.sleep(0.05)
        cam.release()
        return found

    # ---- Autonomous sequence ----
    def run_autonomous():
        print("=== Autonomous sequence started ===")
        overhead_sock = connect_overhead()

        # 1. Navigate to pickup point
        navigate_to(overhead_sock, PICKUP_POINT)
        time.sleep(0.5)

        # 2. Scan for package with onboard camera
        pkg = scan_for_package()
        if pkg is None:
            print("No package found. Stopping.")
            stop()
            return

        # 3. Pick up package
        print("Picking up package...")
        fork_down()
        time.sleep(0.5)
        forward()
        time.sleep(0.8)
        stop()
        time.sleep(0.3)
        fork_up()
        time.sleep(0.5)

        # 4. Reverse away from wall
        print("Reversing...")
        backward()
        time.sleep(1.0)
        stop()
        time.sleep(0.3)

        # 5. Turn around 180
        print("Turning around...")
        right()
        time.sleep(2.0)  # tune for full 180 turn
        stop()
        time.sleep(0.3)

        # 6. Navigate to delivery zone
        navigate_to(overhead_sock, DELIVERY_ZONE)
        time.sleep(0.5)

        # 7. Deliver package
        print("Delivering package...")
        forward()
        time.sleep(0.6)
        stop()
        time.sleep(0.3)
        fork_down()
        time.sleep(0.5)
        backward()
        time.sleep(1.0)
        stop()

        overhead_sock.close()
        print("=== Delivery complete! ===")

    # ---- UDP listener for start command ----
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind(('0.0.0.0', MOTOR_PORT))
    cmd_sock.setblocking(False)

    print("Waiting for start command...")

    try:
        while True:
            try:
                data, _ = cmd_sock.recvfrom(1024)
                msg = data.decode().strip()
                if msg == 'start':
                    run_autonomous()
                elif msg == 'stop':
                    stop()
                    print("Stopped.")
            except BlockingIOError:
                pass
            time.sleep(0.02)
    finally:
        pwm_a.stop()
        pwm_b.stop()
        servo.stop()
        GPIO.cleanup()

# ---- Onboard camera stream (for monitoring) ----
def camera_server():
    app    = Flask(__name__)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def generate_frames():
        while True:
            success, frame = camera.read()
            if not success:
                continue
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    @app.route('/stream')
    def stream():
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    app.run(host='0.0.0.0', port=CAMERA_PORT)

if __name__ == '__main__':
    p1 = Process(target=camera_server)
    p2 = Process(target=motor_server)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
