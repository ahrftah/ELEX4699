# package_identify.py
# Authors: Bardia Jalali and Aiden Higginson
# Standalone test tool: hold a package in front of the onboard camera to read its ArUco ID.

import cv2

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
aruco_params = cv2.aruco.DetectorParameters()
aruco_params.adaptiveThreshWinSizeMin = 3
aruco_params.adaptiveThreshWinSizeMax = 23
aruco_params.adaptiveThreshConstant = 7
aruco_params.minMarkerPerimeterRate = 0.01
detector = cv2.aruco.ArucoDetector(aruco_dict, aruco_params)

camera = cv2.VideoCapture(1, cv2.CAP_DSHOW)

while True:
    success, frame = camera.read()
    if not success:
        break

    corners, ids, _ = detector.detectMarkers(frame)
    if ids is not None:
        for id in ids:
            if id[0] == 38:
                label = f"ID {id[0]} - Package Type 1"
            elif id[0] == 62:
                label = f"ID {id[0]} - Package Type 2"
            else:
                label = f"ID {id[0]} - Unknown"
            print(label)
        cv2.aruco.drawDetectedMarkers(frame, corners, ids)

    cv2.imshow('Package Scanner', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

camera.release()
cv2.destroyAllWindows()
