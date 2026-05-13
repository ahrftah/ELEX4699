import cv2
import time
import motors

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
 
    # ---- Initialize GPIO pins and PWM for motor control and servo ----
    motors.setup_gpio()

    # ---- Main loop ----
    # Move forward for 0.5 seconds
    start_time = time.time()
    end_time = time.time()
    while(end_time - start_time < 3):
        motors.forward(1)
        end_time = time.time()

    # Stop for 1 second
    motors.stop()
    time.sleep(1)

    # Rotate right for 1 seconds
    start_time = time.time()
    while(end_time - start_time < 0.875):
        motors.right(1)
        end_time = time.time()

    # Stop for 1 second
    motors.stop()
    time.sleep(1)

    # Cleanup GPIO on exit
    motors.cleanup_gpio()

if __name__ == "__main__":
    motor_server()