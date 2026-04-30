from flask import Flask, Response
import cv2
import RPi.GPIO as GPIO
from multiprocessing import Process

def motor_server():
    import socket
    import time

    AIN1, AIN2, PWMA = 2, 3, 12
    BIN1, BIN2, PWMB = 17, 27, 13
    SERVO_PIN = 19

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

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', 5001))
    sock.setblocking(False)

    last_received = time.time()
    TIMEOUT = 0.5

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

    app.run(host='0.0.0.0', port=5000)

# Run both
if __name__ == '__main__':
    p1 = Process(target=camera_server)
    p2 = Process(target=motor_server)
    p1.start()
    p2.start()
    p1.join()
    p2.join()
