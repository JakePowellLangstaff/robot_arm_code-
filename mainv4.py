###############################################################################
# Position 1 Test — Smooth Incremental Movement
# Dr Oisin Cawley  |  Mar 2026
#
# Each joint moves in 3 steps from start to goal instead of jumping directly.
###############################################################################

import time
import lss
import lss_const as lssc

lss.initBus("COM7", lssc.LSS_DefaultBaud)

myLSS1 = lss.LSS(1)
myLSS2 = lss.LSS(2)
myLSS3 = lss.LSS(3)
myLSS4 = lss.LSS(4)
myLSS5 = lss.LSS(5)

STEP_WAIT = 1.2   # seconds between each increment — raise for slower movement

def smooth_move(name, servo, start, goal, steps=3):
    """Move a servo from start to goal in equal increments."""
    print(f"  {name}  {start} → {goal}  ({steps} steps)")
    increment = (goal - start) / steps
    for i in range(1, steps + 1):
        pos = int(round(start + increment * i))
        print(f"    step {i}: → {pos}")
        servo.move(pos)
        time.sleep(STEP_WAIT)

# ── STARTING POSITION ─────────────────────────────────────────────────────────
print("=" * 50)
print("STARTING POSITION")
print("=" * 50)

myLSS1.move(-900);  time.sleep(2.0)
myLSS2.move(0);     time.sleep(2.0)
myLSS3.move(0);     time.sleep(2.0)
myLSS4.move(0);     time.sleep(2.0)
myLSS5.move(0);     time.sleep(2.0)

print("\nAt starting position.\n")

# ── SMOOTH MOVE TO POSITION 1 ─────────────────────────────────────────────────
print("=" * 50)
print("MOVING TO POSITION 1")
print("=" * 50 + "\n")

smooth_move("LSS4", myLSS4,    0,  -600)
smooth_move("LSS3", myLSS3,    0,  -900)
smooth_move("LSS2", myLSS2,    0,   900)
smooth_move("LSS2", myLSS2,  900,  1300)   # LSS2 second stage
smooth_move("LSS5", myLSS5,    -600,     0)   # claw — stays closed, edit if needed

print("\nPosition 1 reached.")
del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
lss.closeBus()
print("Done.")
