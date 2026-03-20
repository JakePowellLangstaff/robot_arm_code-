###############################################################################
# Author:               Sebastien Parent-Charette (support@robotshop.com)
# Version:              1.0.0
# Licence:              LGPL-3.0 (GNU Lesser General Public License version 3)
# 
# Description:          Servo 1 (X) + Servo 2 (Y fixed at -600)
# Mar 2026:             Dr Oisin Cawley
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

# Create both servos
myLSS1 = lss.LSS(1)  # X axis (left/right)
myLSS2 = lss.LSS(2)  # Y axis (FIXED at -600)

# Fix Y-axis at -600 (claw elevated, no dragging)
myLSS2.move(-0)
time.sleep(1)
print("LSS2 fixed at -600 (Y elevated)")

# X-axis positions (higher negative=more left, positive=more right)
x_positions = [-600]  # Your confirmed range

# Loop 5 times through X positions (Y stays fixed)
NUM_LOOPS = 5

print(f"Starting {NUM_LOOPS} loops of X-axis movement (Y fixed at -600)...")
print("Press Ctrl+C to stop")

try:
    for loop in range(NUM_LOOPS):
        print(f"\n--- Loop {loop + 1}/{NUM_LOOPS} ---")
        
        # Move X through positions (Y fixed)
        for pos in x_positions:
            print(f"Moving X(LSS1) to: {pos}")
            myLSS1.move(pos)
            time.sleep(0.5)  # Wait for movement
        
        # Return X to center
        print("Returning X to center...")
        myLSS1.move(0)
        time.sleep(1)

    print("\nAll loops completed successfully!")
    
except KeyboardInterrupt:
    print("\nStopped by user (Ctrl+C)")

except Exception as e:
    print(f"Error during movement: {e}")

finally:
    # Safe shutdown: Y stays -600, X centers
    print("Returning X to neutral...")
    myLSS1.move(0)
    myLSS2.move(-600)  # Keep Y elevated
    time.sleep(1)
    
    # Destroy objects
    del myLSS1
    del myLSS2
    
    # Destroy the bus
    lss.closeBus()
    print("Connection closed safely.")

