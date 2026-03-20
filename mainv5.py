###############################################################################
# Author:                Sebastien Parent-Charette (support@robotshop.com)
# Version:               1.0.0
# Licence:               LGPL-3.0 (GNU Lesser General Public License version 3)
# 
# Description:           FULL 5-SERVO TEST: LSS1-5 with Claw (0=closed, 1000=open)
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

# Create ALL FIVE servos
myLSS1 = lss.LSS(1)  # X axis (left/right)
myLSS2 = lss.LSS(2)  # Y axis (FIXED at -600)
myLSS3 = lss.LSS(3)  # Elbow (-1200 lowest → 0 extended)
myLSS4 = lss.LSS(4)  # Wrist (-800 up → 0 neutral → 800 down)
myLSS5 = lss.LSS(5)  # Claw (0=closed → 1000=open)

# Fix Y-axis at -600 (claw elevated)
myLSS2.move(-600)
time.sleep(1)
print("LSS2 fixed at -600 (Y elevated)")

# Home positions
myLSS1.move(0)  # X center
myLSS3.move(0)  # Elbow extended
myLSS4.move(0)  # Wrist neutral
myLSS5.move(1000) # Claw OPEN at start
time.sleep(1)

# Position sets
x_positions = [-600, 0, 600]          # LSS1: left→center→right
elbow_positions = [-1200, 0]          # LSS3: lowest→extended
wrist_positions = [-800, 0, 800]      # LSS4: up→neutral→down
claw_positions = [0, 800]            # LSS5: closed→open

# Loop 5 times
NUM_LOOPS = 5

print(f"FULL 5-Servo test:")
print(f"  X={x_positions}, Y=-600(fixed), Elbow={elbow_positions}")
print(f"  Wrist={wrist_positions}, Claw={claw_positions}")
print("Press Ctrl+C to stop")

try:
    for loop in range(NUM_LOOPS):
        print(f"\n--- Loop {loop + 1}/{NUM_LOOPS} ---")
        
        # 1. X sweep
        print("X sweep...")
        for x_pos in x_positions:
            print(f"  X→{x_pos}")
            myLSS1.move(x_pos)
            time.sleep(0.5)
        
        # 2. Elbow cycle
        print("Elbow cycle...")
        for elbow_pos in elbow_positions:
            print(f"  Elbow→{elbow_pos}")
            myLSS3.move(elbow_pos)
            time.sleep(0.7)
        
        # 3. Wrist cycle
        print("Wrist cycle...")
        for wrist_pos in wrist_positions:
            print(f"  Wrist→{wrist_pos}")
            myLSS4.move(wrist_pos)
            time.sleep(0.5)
        
        # 4. Claw cycle
        print("Claw cycle...")
        for claw_pos in claw_positions:
            print(f"  Claw→{claw_pos} ({'CLOSED' if claw_pos==0 else 'OPEN'})")
            myLSS5.move(claw_pos)
            time.sleep(0.3)
        
        # Home all
        print("→ Home")
        myLSS1.move(0); myLSS3.move(0); myLSS4.move(0); myLSS5.move(1000)
        time.sleep(1)

    print("\nAll 5 servos tested successfully!")
    
except KeyboardInterrupt:
    print("\nStopped by user")

except Exception as e:
    print(f"Error: {e}")

finally:
    # Safe home positions
    print("Safe shutdown...")
    myLSS1.move(0)    # X center
    myLSS2.move(-600) # Y elevated
    myLSS3.move(0)    # Elbow extended
    myLSS4.move(0)    # Wrist neutral
    myLSS5.move(1000) # Claw OPEN
    time.sleep(1)
    
    del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
    lss.closeBus()
    print("Connection closed safely.")
