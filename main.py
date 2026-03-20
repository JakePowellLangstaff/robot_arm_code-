import cv2
import lss
import lss_const as lssc
import numpy as np
import time

# LSS Setup - your exact ranges
lss.initBus("COM7", lssc.LSS_DefaultBaud)
myLSS1 = lss.LSS(1)  # X-axis (left/right rotation)
myLSS2 = lss.LSS(2)  # Y-axis (up/down)
myLSS1.move(0)       # Home X
myLSS2.move(0)       # Home Y (erect)
time.sleep(1)

# Confirmed ranges
LSS1_X = [-30, 0, 40]         # Servo 1: X-axis (left/right)
LSS2_Y = [-1200, -600, 0]     # Servo 2: Y-axis (up/down)

# Camera + red object detection
cap = cv2.VideoCapture(0)
lower_red = np.array([0, 120, 70])    
upper_red = np.array([10, 255, 255])

while True:
    ret, frame = cap.read()
    if not ret: break
    
    # Detect red object
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_red, upper_red)
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    if contours:
        # Biggest red blob
        c = max(contours, key=cv2.contourArea)
        M = cv2.moments(c)
        if M["m00"] != 0:
            cx = int(M["m10"]/M["m00"])  # X center
            cy = int(M["m01"]/M["m00"])  # Y center
            
            # X-axis: left screen→-30, right→+40 (matches your test)
            servo1_pos = int(np.interp(cx, [0, 640], LSS1_X))
            myLSS1.move(servo1_pos * -1)  # Inverted like your test
            
            # Y-axis: top→0(erect), bottom→-1200(lowest)
            servo2_pos = int(np.interp(cy, [0, 480], LSS2_Y))
            
            # Snap Y to safe positions
            if servo2_pos <= -1000:    servo2_pos = -1200
            elif servo2_pos <= -400:   servo2_pos = -600  
            else:                      servo2_pos = 0
            
            myLSS2.move(servo2_pos)
            
            # Visual feedback
            cv2.circle(frame, (cx, cy), 10, (0,255,0), 3)
            cv2.putText(frame, f"X(S1):{servo1_pos} Y(S2):{servo2_pos}", (10,30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    
    cv2.imshow('X+Y TEST - Move RED object', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()
lss.closeBus()
