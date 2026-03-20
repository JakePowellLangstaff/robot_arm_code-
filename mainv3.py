###############################################################################
# Author:                Sebastien Parent-Charette (support@robotshop.com)
# Version:               1.0.0
# Licence:               LGPL-3.0 (GNU Lesser General Public License version 3)
# 
# Description:           LSS1(X) + LSS2(Y fixed -600) + LSS3(extend -1200 to 0)
# Mar 2026:              Dr Oisin Cawley
###############################################################################

# Import required libraries
import time
import serial
import lss
import lss_const as lssc
import cv2  # Keep for future camera integration

# Constants
CST_LSS_Port = "COM7"               # For windows platforms
CST_LSS_Baud = lssc.LSS_DefaultBaud

# Create and open a serial port
lss.initBus(CST_LSS_Port, CST_LSS_Baud)
print("LSS connection done")
print(lss.LSS.bus)

# Create all three servos
myLSS1 = lss.LSS(1)  # X axis (left/right)
myLSS2 = lss.LSS(2)  # Y axis (FIXED at -600)
myLSS3 = lss.LSS(3)  # Elbow extend (lowest -1200 to fully extended 0)

# Fix Y-axis at -600 (claw elevated)
myLSS2.move(-600)
time.sleep(1)
print("LSS2 fixed at -600 (Y elevated)")

# Home positions
myLSS1.move(0)  # X center
myLSS3.move(0)  # Elbow fully extended
time.sleep(1)

# Position sets: X sweeps, Y fixed, Elbow cycles
x_positions = [-600, 0, 600]        # LSS1: left→center→right
elbow_positions = [-1200, 0]        # LSS3: lowest→fully extended

# Loop 5 times
NUM_LOOPS = 5

print(f"Starting {NUM_LOOPS} loops: X={x_positions}, Y=-600(fixed), Elbow={elbow_positions}")
print("Press Ctrl+C to stop")

try:
    for loop in range(NUM_LOOPS):
        print(f"\n--- Loop {loop + 1}/{NUM_LOOPS} ---")
        
        # Full X sweep (Y fixed, Elbow extended)
        print("X sweep (Elbow extended)...")
        for x_pos in x_positions:
            print(f"  X→{x_pos}")
            myLSS1.move(x_pos)
            time.sleep(0.5)
        
        # Elbow cycle (X center, Y fixed)
        print("Elbow cycle (X centered)...")
        for elbow_pos in elbow_positions:
            print(f"  Elbow→{elbow_pos}")
            myLSS3.move(elbow_pos)
            time.sleep(0.7)
        
        # Return to home
        print("Returning to home...")
        myLSS1.move(0)
        myLSS3.move(0)
        time.sleep(1)

    print("\nAll loops completed!")
    
except KeyboardInterrupt:
    print("\nStopped by user (Ctrl+C)")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Safe home: X=0, Y=-600(fixed), Elbow=0(extended)
    print("Safe shutdown...")
    myLSS1.move(0)
    myLSS2.move(-600)
    myLSS3.move(0)
    time.sleep(1)
    
    del myLSS1
    del myLSS2
    del myLSS3
    lss.closeBus()
    print("Connection closed safely.")
