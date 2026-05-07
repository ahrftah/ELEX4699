# Jalali I lov you

from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
from multiprocessing import Process

PORT_1 = 4002
PORT_2 = 5002

def motor_server():
    import socket
    import time

    # ArUco setup
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    # Motor pins
    AIN1, AIN2, PWMA = 4, 17, 18 # pins 7, 11, 12
    BIN1, BIN2, PWMB = 22, 27, 23 # pins 15, 13, 16
    SERVO_PIN = 24 # pin 18

    # GPIO setup
    GPIO.setmode(GPIO.BCM) 
    GPIO.setup([AIN1, AIN2, BIN1, BIN2], GPIO.OUT)
    GPIO.setup([PWMA, PWMB], GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    # PWM setup
    pwm_a = GPIO.PWM(PWMA, 1000)
    pwm_b = GPIO.PWM(PWMB, 1000)
    pwm_a.start(0)
    pwm_b.start(0)

    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)

    


    def communicate_with_warehouse():
        # IP and port of warehouse PC streaming server
        WAREHOUSE_IP = '192.168.0.100'
        WAREHOUSE_PORT = 5002

        # Connect to streaming server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((WAREHOUSE_IP, WAREHOUSE_PORT))

        # Buffer to hold incoming data
        buffer = b''

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

    def fork_down():
        set_angle(20)    # adjust this angle to match your forklift

    def fork_up():
        set_angle(0)   # adjust this angle to match your forklift

    commands = {
        'forward':   lambda: set_motors(1, 0, 1, 0, 60),
        'backward':  lambda: set_motors(0, 1, 0, 1, 60),
        'left':      lambda: set_motors(0, 1, 1, 0, 30),
        'right':     lambda: set_motors(1, 0, 0, 1, 30),
        'stop':      lambda: set_motors(0, 0, 0, 0, 0),
        'fork_up':   fork_up,
        'fork_down': fork_down,
    }

    # UDP server setup
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', PORT_1))
    sock.setblocking(False)

    # Main loop
    last_received = time.time()
    TIMEOUT = 0.5

    directives = ['wait']

    current_directive = 'wait'

    # Initialize camera server in separate process
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

# Camera server
def camera_server():
    app = Flask(__name__)
    camera = cv2.VideoCapture(0)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def generate_frames():
        while True:
            success, frame = camera.read()
            if not success:
                break
            _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

    @app.route('/stream')
    def stream():
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')

    app.run(host='0.0.0.0', port=PORT_1)

# Run both
if __name__ == '__main__':
    p1 = Process(target=camera_server)
    p2 = Process(target=motor_server)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
