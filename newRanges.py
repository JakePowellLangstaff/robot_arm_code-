###############################################################################
#   Author:             Sebastien Parent-Charette (support@robotshop.com)
#   Version:            1.0.0
#   Licence:            LGPL-3.0 (GNU Lesser General Public License version 3)
#   
#   Desscription:       An example using the LSS and the Python module.
#   Mar 2026:           Dr Oisin Cawley
#                       Code to loop Y-axis movements multiple times
###############################################################################

# Import required liraries
import time
import serial

# Import LSS library
import lss
import lss_const as lssc
import cv2 

# Constants
#CST_LSS_Port = "/dev/ttyUSB0"        # For Linux/Unix platforms
CST_LSS_Port = "COM8"               # For windows platforms
CST_LSS_Baud = lssc.LSS_DefaultBaud

# Create and open a serial port
lss.initBus(CST_LSS_Port, CST_LSS_Baud)
print("LSS connection done")
print(lss.LSS.bus)

# Create an LSS object
myLSS2 = lss.LSS(2)

# Define safe Y-axis positions (prevents shutdown)
positions = [-1200,  -600,  -0]

# Loop 5 times through the positions
NUM_LOOPS = 5

print(f"Starting {NUM_LOOPS} loops of Y-axis movement...")
print("Press Ctrl+C to stop")

try:
    for loop in range(NUM_LOOPS):
        print(f"\n--- Loop {loop + 1}/{NUM_LOOPS} ---")
        
        # Move through positions smoothly
        for pos in positions:
            print(f"Moving to Y-position: {pos}")
            myLSS2.move(pos)
            time.sleep(0.5)  # Wait for movement to complete
        
        # Return to starting position
        print("Returning to start position...")
        myLSS2.move(-1200)
        time.sleep(1)

    print("\nAll loops completed successfully!")
    
except KeyboardInterrupt:
    print("\nStopped by user (Ctrl+C)")

except Exception as e:
    print(f"Error during movement: {e}")

finally:
    # Always return to safe position before closing
    print("Returning to safe neutral position...")
    myLSS2.move(0)
    time.sleep(1)
    
    # Destroy objects
    del myLSS2
    
    # Destroy the bus
    lss.closeBus()
    print("Connection closed safely.")

### EOF #######################################################################
