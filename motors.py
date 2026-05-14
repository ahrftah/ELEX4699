import RPi.GPIO as GPIO
import time
import atexit

AIN1, AIN2, PWMA = 4, 17, 18
BIN1, BIN2, PWMB = 22, 27, 12
SERVO_PIN = 24

def setup_gpio():
    print('Initializing GPIO pins')
    start_time = time.time()

    print('Setting up GPIO')
    start_time = time.time()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup([AIN1, AIN2, BIN1, BIN2], GPIO.OUT)
    GPIO.setup([PWMA, PWMB], GPIO.OUT)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    global pwm_a, pwm_b, servo
    pwm_a = GPIO.PWM(PWMA, 1000)
    pwm_b = GPIO.PWM(PWMB, 1000)
    pwm_a.start(0)
    pwm_b.start(0)
    servo = GPIO.PWM(SERVO_PIN, 50)
    servo.start(0)
    end_time = time.time()
    print(f"GPIO setup took {end_time - start_time:.2f} seconds")

def cleanup_gpio():
    # Declare globals so they can be written to (otherwise, only readable)
    global pwm_a, pwm_b, servo
    
    print("\nCleaning up GPIO...")
    try:
        # 1. Stop the PWM signals
        if 'pwm_a' in globals() and pwm_a is not None:
            pwm_a.stop()
        if 'pwm_b' in globals() and pwm_b is not None:
            pwm_b.stop()
        if 'servo' in globals() and servo is not None:
            servo.stop()

        # 2. IMPORTANT: Set them to None so the Garbage Collector 
        # doesn't try to stop them a second time during shutdown.
        pwm_a = None
        pwm_b = None
        servo = None

        # 3. Release the pins
        GPIO.cleanup()
        
    except Exception:
        # During interpreter shutdown, some resources might already be gone.
        # We catch all errors here to ensure a quiet exit.
        pass

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
 
def forward(speed=1):   set_motors(1, 0, 1, 0, 60*speed)
def backward(speed=1):  set_motors(0, 1, 0, 1, 60*speed)
def left(speed=1):      set_motors(0, 1, 1, 0, 30*speed)
def right(speed=1):     set_motors(1, 0, 0, 1, 30*speed)
def stop():      set_motors(0, 0, 0, 0, 0)
def fork_up():   set_angle(0)
def fork_down(): set_angle(20)

setup_gpio()
atexit.register(cleanup_gpio)