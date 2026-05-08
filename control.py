# control.py
# Authors: Bardia Jalali and Aiden Higginson
# Runs on Raspberry Pi. Handles motors, navigation, and package detection.

from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
import socket
import threading
import numpy as np
import math
import time
from skimage.graph import route_through_array

# local imports
import pathfind
import movement

MOTOR_PORT  = 4002
# CAMERA_PORT = 5000

OVERHEAD_IP   = '192.168.0.100'  # replace with overhead camera IP
OVERHEAD_PORT = 5002              # replace with overhead camera port

PICKUP_POINT  = (180, 180)
DELIVERY_ZONE = (190, 584)

directive = 'idle'  # global variable to store current directive (e.g., 'idle', 'start', 'pickup')

#--- Motor and navigation server ----
def motor_server():
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

    # Initialize PWM for motors and servo
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

    # ----------------------------------------------
    # Function name: connect_overhead
    # Description: Establishes a TCP connection to the overhead camera server.
    # Input:  None
    # Output: A connected TCP socket to the overhead camera server.
    # ----------------------------------------------
    def connect_socket(ip, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        return s

    # ----------------------------------------------
    # Function name: get_overhead_frame
    # Description: Requests and receives a JPEG frame from the overhead camera server.
    # Input: A connected TCP socket to the overhead camera server.
    # Output: A decoded OpenCV image (BGR format) or None if decoding fails.
    # ----------------------------------------------
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
            print("Received overhead frame")
            jpg = buf[start:end+2]
            return cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
        return None

    # ----------------------------------------------
    # Function name: get_car_pose
    # Description: Detects the car's position and heading from an overhead frame using ArUco markers.
    # Input: A decoded OpenCV image (BGR format) from the overhead camera.
    # Output: A tuple containing the car's position (x, y) and heading (radians), or (None, None) if not detected.
    # ----------------------------------------------
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

    


    # ----------------------------------------------
    # Function name: navigate_to
    # Description: Navigates the car to a target point using feedback from the overhead camera. Continuously adjusts motor commands based on the car's position and heading until it reaches the target within a specified threshold.
    # Input: - overhead_sock: A connected TCP socket to the overhead camera server.
    #        - target: A tuple (x, y) representing the target coordinates in the overhead camera's frame.
    #        - threshold: A distance threshold (in pixels) for considering the target reached.
    # Output: None. The function will block until the car reaches the target point, at which point it will stop the motors and return.
    # ----------------------------------------------

    # ----------------------------------------------
    # Function name: scan_for_package
    # Description: Uses the onboard camera to scan for packages by detecting specific ArUco markers. Continuously captures frames from the camera and processes them to find markers corresponding to packages until a package is detected or a timeout occurs.
    # Input: - timeout: The maximum time (in seconds) to spend scanning for a package before giving up.
    # Output: The ID of the detected package (e.g., 38 or 62) if found within the timeout period, or None if no package is detected.
    # ----------------------------------------------
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

    def get_binary_map(h, w):


    # ---- Autonomous sequence ----
    def run_autonomous():
        print("=== Autonomous sequence started ===")
        overhead_sock = connect_socket(OVERHEAD_IP, OVERHEAD_PORT)

        if directive is 'pickup':
            print("Directive: Pickup")
            overhead_frame = get_overhead_frame(overhead_sock) # Get initial frame to calculate path
    
            # Get car pose from overhead
            car_pos, heading = get_car_pose(overhead_frame)

            # Calculate path to pickup point
            waypoints = pathfind.pathfind(get_binary_map(600, 600), car_pos, PICKUP_POINT)

            # Follow waypoints to pickup point
            command = None
            while len(waypoints) > 0:
                while command is not 'stop':
                    # Get updated frame and car pose
                    overhead_frame = get_overhead_frame(overhead_sock)
                    car_pos, heading = get_car_pose(overhead_frame)

                    # Calculate motor command based on current pose and next waypoint
                    command = movement.movement(car_pos, waypoints[0], heading)

                    # Send command to motors
                    if command is 'forward':
                        forward()
                    elif command is 'rotate_left':
                        left()
                    elif command is 'rotate_right':
                        right()
                    else:
                        stop() # aligned, check if we reached the waypoint
                    time.sleep(0.1)
                waypoints.pop(0) # Move to next waypoint
            stop() # Ensure we stop at the pickup point

    # ---- UDP listener for start command ----
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind(('0.0.0.0', MOTOR_PORT))
    cmd_sock.setblocking(False)

    print("Waiting for start command...")

    # Communicate with client
    try:
        while True:
            try:
                data, _ = cmd_sock.recvfrom(1024)
                msg = data.decode().strip()
                if msg == 'start' and directive == 'idle':
                    directive = 'pickup'
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

# Multithread the camera and motor server
if __name__ == '__main__':
    motor_server()
