import cv2
import RPi.GPIO as GPIO
import time

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
 
    # ---- Time Variables For Measurement ----
    start_time = None
    end_time = None

    print('Initializing GPIO pins')
    start_time = time.time()
    AIN1, AIN2, PWMA = 4, 17, 18
    BIN1, BIN2, PWMB = 22, 27, 12
    SERVO_PIN = 24
    end_time = time.time()
    print(f"GPIO initialization took {end_time - start_time:.2f} seconds")

    print('Setting up GPIO')
    start_time = time.time()
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
    end_time = time.time()
    print(f"GPIO setup took {end_time - start_time:.2f} seconds")
 
    # ---- Motor helpers ----
    def set_motors(ain1, ain2, bin1, bin2, speed=100):
        motor_adjustment = 0.95
        GPIO.output(AIN1, ain1)
        GPIO.output(AIN2, ain2)
        GPIO.output(BIN1, bin1)
        GPIO.output(BIN2, bin2)
        pwm_a.ChangeDutyCycle(speed)
        pwm_b.ChangeDutyCycle(speed*motor_adjustment)
 
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

    # ---- Main loop ----
    # Move forward for 0.5 seconds
    start_time = time.time()
    end_time = time.time()
    while(end_time - start_time < 2):
        forward()
        end_time = time.time()

    # Stop for 1 second
    stop()
    time.sleep(1)

    # Rotate right for 1 seconds
    start_time = time.time()
    while(end_time - start_time < 1):
        right()
        end_time = time.time()

    # Stop for 1 second
    stop()
    time.sleep(1)

    # Cleanup GPIO on exit
    pwm_a.stop()
    pwm_b.stop()
    servo.stop()
    GPIO.cleanup()

if __name__ == "__main__":
    motor_server()