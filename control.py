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
 
MOTOR_PORT    = 4002
OVERHEAD_IP   = '192.168.0.100'  # replace with overhead camera IP
OVERHEAD_PORT = 5002              # replace with overhead camera port
 
PICKUP_POINT  = (180, 180)
DELIVERY_ZONE = (190, 584)
 
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
    BIN1, BIN2, PWMB = 22, 27, 23
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
    # Function name: get_car_pos
    # Description: Detects the car's position and heading from an overhead frame using ArUco markers.
    # Input: A decoded OpenCV image (BGR format) from the overhead camera.
    # Output: A tuple containing the car's position (x, y) and heading (radians), or (None, None) if not detected.
    # ----------------------------------------------
    def get_car_pos(frame):
        print('get_car_pos')
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
    # Description: Navigates the car through a list of waypoints using feedback from the overhead camera.
    # Input: - waypoints: list of (x, y) tuples to navigate through in order.
    #        - overhead_sock: A connected TCP socket to the overhead camera server.
    # Output: True if all waypoints reached, False if an error occurred.
    # ----------------------------------------------
    def navigate_to(waypoints, overhead_sock):
        if waypoints is None or len(waypoints) == 0:
            print("ERROR: No waypoints provided to navigate_to. Aborting.")
            return False
 
        overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
        if overhead_frame is None:
            print("ERROR: Failed to get overhead frame. Aborting.")
            return False
 
        while len(waypoints) > 0:
            # FIX: reset command for each new waypoint so the inner loop actually runs
            command = None

            while command != 'stop':
                print(f"Navigating to waypoint: {waypoints[0]}")
 
                overhead_frame = None
                while overhead_frame is None:
                    print("Waiting for overhead frame...")
                    overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
                    if overhead_frame is None:
                        print("Error getting overhead frame. Retrying...")
                        time.sleep(0.1)
 
                car_pos, heading = None, None
                while car_pos is None:
                    print("Waiting for car position...")
                    car_pos, heading = get_car_pos(overhead_frame)
                    if car_pos is None:
                        print("Marker not detected, refreshing frame...")
                        time.sleep(0.1)
                        overhead_frame = overhead_socket.get_overhead_frame(overhead_sock)
 
                command = movement.movement(car_pos, waypoints[0], heading)
 
                if command == 'forward':
                    forward()
                elif command == 'rotate_left':
                    left()
                elif command == 'rotate_right':
                    right()
                else:
                    stop()
                time.sleep(0.1)

            waypoints.pop(0)

        stop()
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
        o_sock = overhead_socket.connect_socket(OVERHEAD_IP, OVERHEAD_PORT)
 
        # --- Step 1: Get a valid overhead frame ---
        overhead_frame = None
        while overhead_frame is None:
            print("Waiting for overhead frame...")
            overhead_frame = overhead_socket.get_overhead_frame(o_sock)
            if overhead_frame is None:
                time.sleep(0.5)
        print("Got overhead frame.")
 
        # --- Step 2: Detect car pose ---
        car_pos, heading = None, None
        while car_pos is None:
            print("Waiting for car ArUco marker...")
            car_pos, heading = get_car_pos(overhead_frame)
            if car_pos is None:
                time.sleep(0.1)
                overhead_frame = overhead_socket.get_overhead_frame(o_sock)
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
        navigate_to(waypoints, o_sock)
        print("Reached pickup point.")

        # --- Step 5: Scan for package with onboard camera ---
        cam = cv2.VideoCapture(0)
        pkg_id, center, angle, offset = scanner.scan_for_package(cam, pkg_detector, timeout=20)
        cam.release()

        if pkg_id is None:
            print("No package found. Stopping.")
            stop()
            o_sock.close()
            return
        print(f"Package {pkg_id} found! Picking up...")

        # --- Step 6: Pick up package ---
        fork_down()
        time.sleep(0.5)
        forward()
        time.sleep(0.8)
        stop()
        time.sleep(0.3)
        fork_up()
        time.sleep(0.5)

        # --- Step 7: Reverse away from wall ---
        print("Reversing away from wall...")
        backward()
        time.sleep(1.0)
        stop()
        time.sleep(0.3)

        # --- Step 8: Turn around 180 degrees ---
        print("Turning around...")
        right()
        time.sleep(2.0)  # tune for a full 180 degree turn
        stop()
        time.sleep(0.3)

        # --- Step 9: Get fresh car position for delivery path ---
        print("Computing path to delivery zone...")
        overhead_frame = overhead_socket.get_overhead_frame(o_sock)
        car_pos, heading = None, None
        while car_pos is None:
            car_pos, heading = get_car_pos(overhead_frame)
            if car_pos is None:
                time.sleep(0.1)
                overhead_frame = overhead_socket.get_overhead_frame(o_sock)
 
        # --- Step 10: Compute path to delivery ---
        waypoints = pathfind.pathfind(get_binary_map(600, 600), car_pos, DELIVERY_ZONE)
        if not waypoints:
            print("ERROR: Pathfinder returned no waypoints to delivery. Aborting.")
            return
        print(f"Delivery path found: {len(waypoints)} waypoints.")
 
        # --- Step 11: Drive to delivery ---
        print("Navigating to delivery zone...")
        navigate_to(waypoints, o_sock)

        # --- Step 12: Drop off package ---
        print("Dropping off package...")
        forward()
        time.sleep(0.6)
        stop()
        time.sleep(0.3)
        fork_down()
        time.sleep(0.5)
        backward()
        time.sleep(1.0)
        stop()

        o_sock.close()
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
                    try:
                        run_autonomous()
                    except Exception as e:
                        print(f"Error in autonomous sequence: {e}")
                        stop()
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
 
if __name__ == '__main__':
    motor_server()
