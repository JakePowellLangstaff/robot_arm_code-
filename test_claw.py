###############################################################################
# Claw Test — LSS5 open/close
# Dr Oisin Cawley  |  Mar 2026
###############################################################################



# 0 is fully closed, 600 is fully open. 

import time
import lss
import lss_const as lssc

CST_LSS_Port = "COM7"
CST_LSS_Baud = lssc.LSS_DefaultBaud

lss.initBus(CST_LSS_Port, CST_LSS_Baud)
myLSS5 = lss.LSS(5)

print("Claw test starting...")
print("  0   = fully closed")
print("  600 = fully open\n")

try:
    while True:
        print("Opening claw → 500")
        myLSS5.move(-500)
        time.sleep(2)

        print("Closing claw → 0")
        myLSS5.move(1)
        time.sleep(2)

except KeyboardInterrupt:
    print("\nStopped — closing claw and shutting down.")

finally:
    myLSS5.move(0)
    time.sleep(1)
    del myLSS5
    lss.closeBus()
    print("Done.")
