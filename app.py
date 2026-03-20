
###############################################################################
#	Author:			Sebastien Parent-Charette (support@robotshop.com)
#	Version:		1.0.0
#	Licence:		LGPL-3.0 (GNU Lesser General Public License version 3)
#	
#	Desscription:	An example using the LSS and the Python module.
#	Mar 2026:		Dr Oisin Cawley
#					Code to show the ranges of the different servos.
###############################################################################

# Import required liraries
import time
import serial

# Import LSS library
import lss
import lss_const as lssc

# Constants
#CST_LSS_Port = "/dev/ttyUSB0"		# For Linux/Unix platforms
CST_LSS_Port = "COM7"				# For windows platforms
CST_LSS_Baud = lssc.LSS_DefaultBaud

# Create and open a serial port
lss.initBus(CST_LSS_Port, CST_LSS_Baud)
print("LSS connection done")
print(lss.LSS.bus)

# Create an LSS object
myLSS1 = lss.LSS(1)
myLSS2 = lss.LSS(2)
myLSS3 = lss.LSS(3)
myLSS4 = lss.LSS(4)
myLSS5 = lss.LSS(5)
print("LSS object1: " + str(myLSS1.getPosition()))
print("LSS object2: " + str(myLSS2.getPosition()))
print("LSS object3: " + str(myLSS3.getPosition()))
print("LSS object4: " + str(myLSS4.getPosition()))
print("LSS object5: " + str(myLSS5.getPosition()))

# Initialize LSS to position 0.0 deg
myLSS1.move(-120)
myLSS2.move(-800)
myLSS3.move(550)
myLSS4.move(300)
myLSS5.move(0)


print("Move done.")
time.sleep(1)

#The following for the Gripper range (actuator 5)
#range 0(closed) to 850
for i in range(0,850):
    print("Trying position: " + str(i))
    myLSS5.move(i*-1)
    time.sleep(.03) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper

#The following for actuator 2 (bottom arm)
# -900 is about parallel with ground
#lss4Position = int(myLSS4.getPosition())
#for i in range(-900,-250):
    #print("Trying position: " + str(i))
    #myLSS2.move(i)
    #time.sleep(.03) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper
    #lss4Position = lss4Position-1
    #myLSS4.move(lss4Position)

#The following for actuator 3 (top arm)
# -850/850 is parallel to bottom arm, 0 is straight up
#for i in range(-850,100): 
    #print("Trying position: " + str(i))
    #myLSS3.move(i*-1)
    #time.sleep(.03) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper

#The following for actuator 4
# About -800 is straight up, 0 is straight out from arm
#lss4Position = int(myLSS4.getPosition())
#for i in range(lss4Position, -800, -1):
 #   print("Trying position: " + str(i))
  #  myLSS4.move(i)
   # time.sleep(.03) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper

#The following for actuator 1
#
for i in range(-30,40):
    print("Trying position: " + str(i))
    myLSS1.move(i*-1)
    time.sleep(.05) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper


# Destroy objects
del myLSS1
del myLSS2
del myLSS3
del myLSS4
del myLSS5

# Destroy the bus
lss.closeBus()

### EOF #######################################################################