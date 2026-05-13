import RPi.GPIO as GPIO
import time

def setup_gpio():
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

def cleanup_gpio():
    pwm_a.stop()
    pwm_b.stop()
    servo.stop()
    GPIO.cleanup()

# ---- Motor helpers ----
def set_motors(ain1, ain2, bin1, bin2, speed=100):
    motor_adjustment = 0.95 # Adjust this value to balance the motors
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
 
def forward(speed):   set_motors(1, 0, 1, 0, 60*speed)
def backward(speed):  set_motors(0, 1, 0, 1, 60*speed)
def left(speed):      set_motors(0, 1, 1, 0, 30*speed)
def right(speed):     set_motors(1, 0, 0, 1, 30*speed)
def stop():      set_motors(0, 0, 0, 0, 0)
def fork_up():   set_angle(0)
def fork_down(): set_angle(20)