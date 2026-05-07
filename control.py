# control.py
# Authors: Bardia Jalali and Aiden Higginson
# Runs on Raspberry Pi. Starts motor server and onboard camera server.

from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
from multiprocessing import Process
import socket
import threading
import time

MOTOR_PORT  = 4002
CAMERA_PORT = 5000

# Replace with your PC's IP address (run ipconfig on Windows to find it)
PC_IP          = '192.168.0.xxx'
PC_DETECT_PORT = 4003

# ---- Motor server ----
def motor_server():
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

    commands = {
        'forward':   lambda: set_motors(1, 0, 1, 0, 60),
        'backward':  lambda: set_motors(0, 1, 0, 1, 60),
        'left':      lambda: set_motors(0, 1, 1, 0, 30),
        'right':     lambda: set_motors(1, 0, 0, 1, 30),
        'stop':      lambda: set_motors(0, 0, 0, 0, 0),
        'fork_up':   lambda: set_angle(0),
        'fork_down': lambda: set_angle(20),
    }

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', MOTOR_PORT))
    sock.setblocking(False)

    last_received = time.time()
    TIMEOUT = 0.5

    print("Motor server running...")
    try:
        while True:
            latest = None
            while True:
                try:
                    data, _ = sock.recvfrom(1024)
                    latest = data.decode().strip()
                    last_received = time.time()
                except BlockingIOError:
                    break

            if latest and latest in commands:
                commands[latest]()
            elif time.time() - last_received > TIMEOUT:
                set_motors(0, 0, 0, 0, 0)

            time.sleep(0.02)
    finally:
        pwm_a.stop()
        pwm_b.stop()
        servo.stop()
        GPIO.cleanup()

# ---- Camera + detection server ----
def camera_server():
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    aruco_params = cv2.aruco.DetectorParameters()
    aruco_params.adaptiveThreshWinSizeMin = 3
    aruco_params.adaptiveThreshWinSizeMax = 23
    aruco_params.adaptiveThreshConstant = 7
    aruco_params.minMarkerPerimeterRate = 0.01
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    detect_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    latest_frame = None
    frame_lock = threading.Lock()

    def capture_loop():
        nonlocal latest_frame
        while True:
            success, frame = camera.read()
            if not success:
                continue

            corners, ids, _ = detector.detectMarkers(frame)
            if ids is not None:
                for id in ids:
                    if id[0] in [38, 62]:
                        msg = f"PACKAGE_{id[0]}"
                        detect_sock.sendto(msg.encode(), (PC_IP, PC_DETECT_PORT))
                        print(f"Sent detection: {msg}")

            with frame_lock:
                latest_frame = frame.copy()

    threading.Thread(target=capture_loop, daemon=True).start()

    app = Flask(__name__)

    def generate_frames():
        while True:
            with frame_lock:
                frame = latest_frame
            if frame is None:
                continue
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    @app.route('/stream')
    def stream():
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    print("Camera server running...")
    app.run(host='0.0.0.0', port=CAMERA_PORT)

# ---- Run both ----
if __name__ == '__main__':
    p1 = Process(target=camera_server)
    p2 = Process(target=motor_server)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
