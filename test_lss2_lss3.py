###############################################################################
# LSS2 + LSS3 Isolation Test
# Dr Oisin Cawley  |  Mar 2026
#
# Moves LSS2 and LSS3 through a small safe range step by step.
# Watch the arm and note where it hits its physical limits.
# Edit the positions list at the top to home in on your new arm's range.
#
# LSS2  shoulder :  0 = up  |  increasingly negative = lowering toward ground
# LSS3  elbow    :  0 = straight  |  increasingly negative = bending inward
###############################################################################

import time
import lss
import lss_const as lssc

CST_LSS_Port = "COM7"
CST_LSS_Baud = lssc.LSS_DefaultBaud

# ── EDIT THESE TO FIND YOUR NEW ARM'S SAFE RANGE ─────────────────────────────
# Start conservative and widen once you see how far it actually goes.

LSS2_POSITIONS = [0, -200, -400, -500, -600, -700]   # shoulder steps
LSS3_POSITIONS = [0, -200, -400, -500, -600, -700]   # elbow steps

STEP_WAIT = 2.0   # seconds between each step (increase if arm is slow)
# ─────────────────────────────────────────────────────────────────────────────

lss.initBus(CST_LSS_Port, CST_LSS_Baud)
myLSS2 = lss.LSS(2)
myLSS3 = lss.LSS(3)

print("LSS2 + LSS3 isolation test")
print(f"  LSS2 positions: {LSS2_POSITIONS}")
print(f"  LSS3 positions: {LSS3_POSITIONS}")
print("Press Ctrl+C to stop at any point\n")

try:
    # ── TEST LSS2 ALONE ───────────────────────────────────────────────────────
    print("--- LSS2 (shoulder) test --- LSS3 stays at 0")
    myLSS3.move(0)
    time.sleep(STEP_WAIT)

    for pos in LSS2_POSITIONS:
        print(f"  LSS2 → {pos}")
        myLSS2.move(pos)
        time.sleep(STEP_WAIT)

    print("  LSS2 → 0 (returning to safe)")
    myLSS2.move(0)
    time.sleep(STEP_WAIT)

    # ── TEST LSS3 ALONE ───────────────────────────────────────────────────────
    print("\n--- LSS3 (elbow) test --- LSS2 stays at 0")
    myLSS2.move(0)
    time.sleep(STEP_WAIT)

    for pos in LSS3_POSITIONS:
        print(f"  LSS3 → {pos}")
        myLSS3.move(pos)
        time.sleep(STEP_WAIT)

    print("  LSS3 → 0 (returning to safe)")
    myLSS3.move(0)
    time.sleep(STEP_WAIT)

    # ── TEST BOTH TOGETHER ────────────────────────────────────────────────────
    print("\n--- LSS2 + LSS3 combined (paired steps) ---")
    for s2, s3 in zip(LSS2_POSITIONS, LSS3_POSITIONS):
        print(f"  LSS2 → {s2}  |  LSS3 → {s3}")
        myLSS2.move(s2)
        myLSS3.move(s3)
        time.sleep(STEP_WAIT)

    print("\nTest complete.")

except KeyboardInterrupt:
    print("\nStopped by user.")

finally:
    print("Returning both to 0...")
    myLSS2.move(0)
    myLSS3.move(0)
    time.sleep(1.5)
    del myLSS2, myLSS3
    lss.closeBus()
    print("Done.")
