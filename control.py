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
import scanner
import overhead_socket
 
MOTOR_PORT  = 4002
# CAMERA_PORT = 5000
 
OVERHEAD_IP   = '192.168.0.100'  # replace with overhead camera IP
OVERHEAD_PORT = 5002              # replace with overhead camera port
 
PICKUP_POINT  = (180, 180)
DELIVERY_ZONE = (190, 584)
 
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
 
    print('Initializing GPIO pins')
    AIN1, AIN2, PWMA = 4, 17, 18
    BIN1, BIN2, PWMB = 22, 27, 23
    SERVO_PIN = 24
    print('Setting up GPIO')
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
    # Function name: get_car_pose
    # Description: Detects the car's position and heading from an overhead frame using ArUco markers.
    # Input: A decoded OpenCV image (BGR format) from the overhead camera.
    # Output: A tuple containing the car's position (x, y) and heading (radians), or (None, None) if not detected.
    # ----------------------------------------------
    def get_car_pos(frame):
        print('get car_pos')
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
    def navigate_to(waypoints, overhead_sock):
        # Guard: no waypoints
        if waypoints is None or len(waypoints) == 0:
            print("ERROR: No waypoints provided to navigate_to. Aborting navigation.")
            return False
 
        # Guard: ensure we can get overhead frame and car position before starting navigation
        overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
        if overhead_frame is None:
            print("ERROR: Failed to get overhead frame. Aborting navigation.")
            return False
 
        # Main navigation loop: iterate through waypoints, adjusting motor commands based on current pose until we reach each waypoint within a threshold
        command = None
        while len(waypoints) > 0:
            # Guard: ensure we can get overhead frame and car position at the start of each waypoint navigation
            # We will attempt to get the overhead frame and car position, and if we fail, we will print an error and break out of the loop to stop navigation.
            # This way we avoid sending potentially dangerous motor commands if we lose tracking of the car.
            
 
            while command != 'stop':
                print(f"Navigating to waypoint: {waypoints[0]}")
 
                # Get updated frame and car pose
                overhead_frame, car_pos = None, None
                while overhead_frame is None:
                    print("Waiting for overhead frame...")
                    overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
                    if overhead_frame is None:
                        print("Error getting overhead frame. Retrying...")
                        time.sleep(0.1)
 
                while car_pos is None:
                    print("Waiting for car position...")
                    car_pos, heading = get_car_pos(overhead_frame)
                    if car_pos is None:
                        print("Marker not detected, refreshing frame...")
                        time.sleep(0.1)
                        overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
 
                # Calculate motor command based on current pose and next waypoint
                command = movement.movement(car_pos, waypoints[0], heading)
 
                # Send command to motors
                if command == 'forward':
                    forward()
                elif command == 'rotate_left':
                    left()
                elif command == 'rotate_right':
                    right()
                else:
                    stop() # aligned, check if we reached the waypoint
                time.sleep(0.1)
            waypoints.pop(0) # Move to next waypoint
        stop() # Ensure we stop at the pickup point
        # Successfully reached the target
        return True
 
    def get_binary_map(width, height):
        binary_obstacles = np.zeros((height, width), dtype=np.uint8)
        cv2.rectangle(binary_obstacles, (0, 0), (width-1, height-1), 255, 3)
        cv2.rectangle(binary_obstacles, (110, 440), (130, 599), 255, -1)
        cv2.rectangle(binary_obstacles, (480, 480), (495, 599), 255, -1)
        cv2.rectangle(binary_obstacles, (270, 220), (330, 240), 255, -1)
        return binary_obstacles
 
 
    # ---- Autonomous sequence ----
    def run_autonomous():
        print("=== Autonomous sequence started ===")
        overhead_sock = overhead_socket.connect_socket(OVERHEAD_IP, OVERHEAD_PORT)
 
        # --- Step 1: Get a valid overhead frame (retry until one arrives) ---
        overhead_frame = None
        while overhead_frame is None:
            print("Waiting for overhead frame...")
            overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
            if overhead_frame is None:
                time.sleep(0.5)
        print("Got overhead frame.")
 
        # --- Step 2: Detect car pose (retry across fresh frames until marker found) ---
        car_pos, heading = None, None
        while car_pos is None:
            print("Waiting for car ArUco marker...")
            car_pos, heading = get_car_pos(overhead_frame)
            if car_pos is None:
                time.sleep(0.1)
                overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
        print(f"Car detected at {car_pos}, heading {heading:.2f} rad.")
 
        # --- Step 3: Compute path to pickup ---
        print("Computing path to pickup point...")
        waypoints = pathfind.pathfind(get_binary_map(600, 600), car_pos, PICKUP_POINT)
        if not waypoints:
            print("ERROR: Pathfinder returned no waypoints. Aborting.")
            return
        print(f"Path found: {len(waypoints)} waypoints.")
 
        # --- Step 4: Drive to pickup ---
        print("Navigating to pickup point...")
        navigate_to(waypoints, overhead_sock)
 
        # --- Step 5: Compute path to delivery ---
        print("Computing path to delivery zone...")
        overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
        car_pos, heading = None, None
        while car_pos is None:
            car_pos, heading = get_car_pos(overhead_frame)
            if car_pos is None:
                time.sleep(0.1)
                overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
 
        waypoints = pathfind.pathfind(get_binary_map(600, 600), car_pos, DELIVERY_ZONE)
        if not waypoints:
            print("ERROR: Pathfinder returned no waypoints to delivery. Aborting.")
            return
        print(f"Delivery path found: {len(waypoints)} waypoints.")
 
        # --- Step 6: Drive to delivery ---
        print("Navigating to delivery zone...")
        navigate_to(waypoints, overhead_sock)
        print("=== Autonomous sequence complete ===")
 
    # ---- UDP listener for start command ----
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind(('0.0.0.0', MOTOR_PORT))
    cmd_sock.setblocking(False)
 
    print("Waiting for start command...")
 
    msg = None
 
    # Communicate with client
    try:
        while True:
            try:
                data, _ = cmd_sock.recvfrom(1024)
                msg = data.decode().strip()
                if msg == 'start':
                    try:
                        run_autonomous()
                    except Exception as e:
                        print(f"Error occurred while running autonomous sequence: {e}")
                elif msg == 'stop':
                    stop()
                    print("Stopped.")
            except BlockingIOError:
                pass
            time.sleep(0.02)
    finally:
        print("Cleaning up GPIO and exiting.")
        pwm_a.stop()
        pwm_b.stop()
        servo.stop()
        GPIO.cleanup()
 
 
# Multithread the camera and motor server
if __name__ == '__main__':
    motor_server()