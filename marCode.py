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


#range 0(closed) to 850
for i in range(0,850):
    print("Trying position: " + str(i))
    myLSS5.move(i*-1)
   time.sleep(.03) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper
for i in range(-30,40):
    print("Trying position: " + str(i))
    myLSS1.move(i*-1)
    time.sleep(.05) #0.03 seems to be  the minmum delay to get smooth movement on the Gripper
