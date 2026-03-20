###############################################################################
# Author:                Sebastien Parent-Charette (support@robotshop.com)
# Version:               1.0.0
# Licence:               LGPL-3.0 (GNU Lesser General Public License version 3)
# 
# Description:           FULL 5-SERVO CAMERA TRACKING (Red object controls ALL)
# Mar 2026:              Dr Oisin Cawley
###############################################################################

# Import required libraries
import cv2
import lss
import lss_const as lssc
import numpy as np
import time

# LSS Setup + ALL servos
CST_LSS_Port = "COM7"
lss.initBus(CST_LSS_Port, lssc.LSS_DefaultBaud)
print("LSS connection established")

myLSS1 = lss.LSS(1)  # X axis
myLSS2 = lss.LSS(2)  # Y axis  
myLSS3 = lss.LSS(3)  # Elbow
myLSS4 = lss.LSS(4)  # Wrist
myLSS5 = lss.LSS(5)  # Claw (dead but included)

# Home positions first
myLSS1.move(0); myLSS2.move(-600); myLSS3.move(0); myLSS4.move(0); myLSS5.move(1000)
time.sleep(2)
print("Arm homed - Move RED object to control!")

# CONFIRMED RANGES from your tests
SERVO_RANGES = {
    1: [-600, 600],      # LSS1 X: left→right
    2: [-1200, 0],       # LSS2 Y: low→erect
    3: [-1200, 0],       # LSS3 Elbow: low→extended
    4: [-800, 800],      # LSS4 Wrist: up→down
    5: [0, 1000]         # LSS5 Claw: closed→open
}

# Camera + Red detection
cap = cv2.VideoCapture(0)
lower_red = np.array([0, 120, 70])
upper_red = np.array([10, 255, 255])

print("=== LIVE TRACKING ACTIVE ===")
print("Move RED object in frame to control all servos!")
print("Press 'q' to quit")

while True:
    ret, frame = cap.read()
    if not ret: break
    
    h, w = frame.shape[:2]
    
    # Red object detection
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_red, upper_red)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Biggest red object
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])  # X center
            cy = int(M["m01"]/M["m00"])  # Y center
            area = cv2.contourArea(c)     # Size for claw
            
            # MAP screen position → servo positions
            # LSS1 X: screen-left → -600, screen-right → 600
            lss1_pos = int(np.interp(cx, [0, w], SERVO_RANGES[1]))
            myLSS1.move(lss1_pos)
            
            # LSS2 Y: screen-top → 0(erect), screen-bottom → -1200
            lss2_pos = int(np.interp(cy, [0, h], SERVO_RANGES[2]))
            myLSS2.move(lss2_pos)
            
            # LSS3 Elbow: follows Y (same as LSS2 for coordination)
            lss3_pos = int(np.interp(cy, [0, h], SERVO_RANGES[3]))
            myLSS3.move(lss3_pos)
            
            # LSS4 Wrist: follows X (slight tilt tracking)
            lss4_pos = int(np.interp(cx, [0, w], SERVO_RANGES[4]))
            myLSS4.move(lss4_pos)
            
            # LSS5 Claw: object size (big=close, small=open)
            claw_norm = np.clip(area / 5000, 0, 1)  # Normalize area
            lss5_pos = int(np.interp(claw_norm, [0, 1], SERVO_RANGES[5]))
            myLSS5.move(lss5_pos)
            
            # Visual feedback
            cv2.circle(frame, (cx, cy), 10, (0,255,0), 3)
            cv2.putText(frame, f"X1:{lss1_pos} Y2:{lss2_pos} E3:{lss3_pos}", (10,30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
            cv2.putText(frame, f"W4:{lss4_pos} C5:{lss5_pos} Area:{area:.0f}", (10,60), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    
    cv2.imshow('FULL ARM TRACKING - Move RED object!', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()

# Safe shutdown
print("Shutting down safely...")
myLSS1.move(0); myLSS2.move(-600); myLSS3.move(0); myLSS4.move(0); myLSS5.move(1000)
time.sleep(1)

del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
lss.closeBus()
print("Complete shutdown.")
