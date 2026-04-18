###############################################################################
# Position 1 + Position 2 + Return to Start
# Dr Oisin Cawley  | April 2026
#
# HOW TO TUNE SMOOTHNESS PER JOINT:
#   Increase steps= on any smooth_move line to make that joint smoother.
#   Increase STEP_WAIT to slow everything down globally.
#   open palm reutrns it home for emergency 
################################################################################

import time
import lss
import lss_const as lssc

lss.initBus("COM7", lssc.LSS_DefaultBaud)

myLSS1 = lss.LSS(1)
myLSS2 = lss.LSS(2)
myLSS3 = lss.LSS(3)
myLSS4 = lss.LSS(4)
myLSS5 = lss.LSS(5)

STEP_WAIT = 1.2   # seconds between every single increment — raise to slow all joints

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

myLSS1.move(-900);  time.sleep(2.0)    # base rotation
myLSS2.move(0);     time.sleep(2.0)    # shoulder
myLSS3.move(0);     time.sleep(2.0)    # elbow
myLSS4.move(0);     time.sleep(2.0)    # wrist
myLSS5.move(-600);  time.sleep(2.0)    # claw open

print("\nAt starting position.\n")

# ── SMOOTH MOVE TO POSITION 1 ─────────────────────────────────────────────────
print("=" * 50)
print("MOVING TO POSITION 1")
print("=" * 50 + "\n")

smooth_move("LSS4", myLSS4,    0,   -600, steps=5)   # wrist
smooth_move("LSS3", myLSS3,    0,   -900, steps=5)   # elbow
smooth_move("LSS2", myLSS2,    0,    900, steps=5)   # shoulder stage 1
smooth_move("LSS2", myLSS2,  900,   1300, steps=5)   # shoulder stage 2
smooth_move("LSS5", myLSS5, -600,      0, steps=4)   # close claw — grip item

print("\nPosition 1 reached — item gripped.\n")
time.sleep(1.5)

# ── SMOOTH MOVE TO POSITION 2 ─────────────────────────────────────────────────
print("=" * 50)
print("MOVING TO POSITION 2")
print("=" * 50 + "\n")

smooth_move("LSS4", myLSS4, -600,   -800, steps=4)    # wrist adjust
smooth_move("LSS1", myLSS1, -900,    900, steps=10)   # base rotation — big sweep
smooth_move("LSS4", myLSS4, -800,   -600, steps=4)    # wrist settle
smooth_move("LSS5", myLSS5,    0,   -600, steps=4)    # open claw — release item

print("\nPosition 2 reached — item released.\n")
time.sleep(1.5)

# ── RETURN TO START ───────────────────────────────────────────────────────────
print("=" * 50)
print("RETURNING TO START")
print("=" * 50 + "\n")

# Shoulder first — bring arm up before anything else moves
smooth_move("LSS2", myLSS2, 1300,    900, steps=5)   # shoulder stage 1 reverse
smooth_move("LSS2", myLSS2,  900,      0, steps=5)   # shoulder stage 2 reverse

# Elbow next
smooth_move("LSS3", myLSS3, -900,      0, steps=5)   # elbow back to 0

# Wrist next
smooth_move("LSS4", myLSS4, -600,      0, steps=5)   # wrist back to 0

# Claw stays at -600 (open) — no move needed

# Base last — rotate back to start
smooth_move("LSS1", myLSS1,  900,   -900, steps=10)  # base rotation back — big sweep

print("\nBack at starting position — ready for next cycle.")

# ── SHUTDOWN ──────────────────────────────────────────────────────────────────
del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
lss.closeBus()
print("Done.")