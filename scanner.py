import math
import cv2
import time
import numpy as np

def scan_for_package(cam, pkg_detector, timeout=20):
    print("Scanning for package...")
    
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    deadline = time.time() + timeout
    found_id = None
    target_center = None
    angle = 0.0
    alignment_error = 0

    while time.time() < deadline:
        success, frame = cam.read()
        if not success:
            continue

        corners, ids, _ = pkg_detector.detectMarkers(frame)
        
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in [38, 62]:
                    found_id = marker_id
                    marker_corners = corners[i][0]
                    
                    cx = int(np.mean(marker_corners[:, 0]))
                    cy = int(np.mean(marker_corners[:, 1]))
                    target_center = (cx, cy)
                    
                    # Logic: Alignment and Angle
                    alignment_error = cx - 320 
                    # 1.08 radians is approx 62 degrees (Pi Cam FOV)
                    angle = (alignment_error / 640) * 1.08 

                    # Draw for feedback (only if you have a display)
                    cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)
                    break
            
            if found_id:
                break
        
        # Uncomment if using a monitor/VNC, otherwise keep commented for Pi 4 stability
        # cv2.imshow("Scanner", frame)
        # if cv2.waitKey(1) & 0xFF == ord('q'): break
            
        time.sleep(0.01)
        
    return found_id, target_center, angle, alignment_error

if __name__ == "__main__":
    camera = cv2.VideoCapture(0)
    
    # Using 8x8_100 to ensure the dictionary exists in standard builds
    aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
    aruco_params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

    try:
        # 1. UNPACK ALL FOUR RETURN VALUES
        package_id, center, final_angle, offset = scan_for_package(camera, detector, timeout=10)

        if package_id:
            print("-" * 30)
            print(f"SUCCESS: Found Package {package_id}")
            print(f"Center Pixel: {center}")
            # Convert radians to degrees for readability
            print(f"Angle from Center: {math.degrees(final_angle):.2f} degrees")
            print(f"Alignment Offset: {offset} pixels")
            print("-" * 30)
        else:
            print("FAILED: No package detected within timeout.")

    finally:
        camera.release()
        cv2.destroyAllWindows()