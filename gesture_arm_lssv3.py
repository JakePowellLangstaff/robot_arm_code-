###############################################################################
# Gesture-Controlled Robot Arm — LSS1–LSS5
# Dr Oisin Cawley  |  April 2026
# MediaPipe 0.10+ (Tasks API)
#
# GESTURES:
#   Open palm  (all fingers up)  HOME emergency reset  (return to starting position)
#   One finger (index only)      PICKUP_SEQUENCE_1  (pick up item)
#   Peace sign (index+middle)    PICKUP_SEQUENCE_2  (drop off item + return)
#
# CONFIRMED JOINT RANGES:
#   LSS1  base      :  0=straight  | -=right        | +=left
#   LSS2  shoulder  :  0=down      | +=up (600=nearly upright, 1300=max)
#   LSS3  elbow     :  0=parallel  | -=down (-900=lowest)
#   LSS4  wrist     :  0=neutral   | -=down (-800=lowest)
#   LSS5  claw      :  -600=open   | 0=closed
#
# FIRST RUN: downloads hand_landmarker.task (~8 MB) automatically
# REQUIRES:  pip install mediapipe opencv-python
###############################################################################

import os
import time
import urllib.request
import threading
import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import lss
import lss_const as lssc

# ── CONFIG ────────────────────────────────────────────────────────────────────
CST_LSS_Port = "COM7"
CST_LSS_Baud = lssc.LSS_DefaultBaud
CAMERA_INDEX = 0
CONFIDENCE   = 0.75

MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = "hand_landmarker.task"
# ─────────────────────────────────────────────────────────────────────────────


#
#              SEQUENCES — EDIT STEPS= OR WAIT= VALUES TO TUNE            
#
#   Each step moves one joint to a position then waits.                     
#   Steps are broken into small increments to keep movement smooth.         
#   Increase "wait" on any step if the servo hasn't finished moving.        
#

# Sequences are expanded from smooth_move(steps=) calls in the position test
# script so movement is identical — just expressed as individual waypoints.

PICKUP_SEQUENCE_1 = [
    # ── Pick up item — faithfully expanded from position test script ──────────
    # Arm HOLDS at end — make OPEN PALM to return home

    # LSS4 wrist:  0 → -600  (5 steps of -120)
    {"lss4": -120, "wait": 0.6},
    {"lss4": -240, "wait": 0.6},
    {"lss4": -360, "wait": 0.6},
    {"lss4": -480, "wait": 0.6},
    {"lss4": -600, "wait": 0.6},
    {"lss4": -700, "wait": 0.6},   # extra step to make wrist a bit smoother

    # LSS3 elbow:  0 → -900  (5 steps of -180)
    {"lss3": -180, "wait": 0.9},
    {"lss3": -360, "wait": 0.9},
    {"lss3": -540, "wait": 0.9},
    {"lss3": -720, "wait": 0.9},
    {"lss3": -900, "wait": 0.9},

    # LSS2 shoulder stage 1:  0 → 900  (5 steps of 180)
    {"lss2":  180, "wait": 0.9},
    {"lss2":  360, "wait": 0.9},
    {"lss2":  540, "wait": 0.9},
    {"lss2":  720, "wait": 0.9},
    {"lss2":  900, "wait": 0.9},

    # LSS2 shoulder stage 2:  900 → 1300  (5 steps of 80)
    {"lss2":  980, "wait": 0.9},
    {"lss2": 1060, "wait": 0.9},
    {"lss2": 1140, "wait": 0.9},
    {"lss2": 1220, "wait": 0.9},
    {"lss2": 1300, "wait": 0.9},

    # LSS5 claw close:  -600 → 0  (4 steps of 150)
    {"lss5": -450, "wait": 0.9},
    {"lss5": -300, "wait": 0.9},
    {"lss5": -150, "wait": 0.9},
    {"lss5":   -5, "wait": 0.9},

    # ── HOLDS HERE with item gripped — show OPEN PALM to go home ─────────────
]

PICKUP_SEQUENCE_2 = [
    # ── Drop off item then return to starting position ────────────────────────
    # Sequence ends back at home — no gesture needed to reset

    # LSS4 wrist adjust:  -600 → -800  (4 steps of -50)
    {"lss4": -650, "wait": 0.9},
    {"lss4": -700, "wait": 0.9},
    {"lss4": -750, "wait": 0.9},
    {"lss4": -800, "wait": 0.9},

    # LSS1 base rotation:  -900 → 900  (10 steps of 180) — big sweep, keep fine
    {"lss1": -720, "wait": 1.2},
    {"lss1": -540, "wait": 1.2},
    {"lss1": -360, "wait": 1.2},
    {"lss1": -180, "wait": 1.2},
    {"lss1":    0, "wait": 1.2},
    {"lss1":  180, "wait": 1.2},
    {"lss1":  360, "wait": 1.2},
    {"lss1":  540, "wait": 1.2},
    {"lss1":  720, "wait": 1.2},
    {"lss1":  900, "wait": 1.2},

    # LSS4 wrist settle:  -800 → -600  (4 steps of 50)
    {"lss4": -750, "wait": 0.9},
    {"lss4": -700, "wait": 0.9},
    {"lss4": -650, "wait": 0.9},
    {"lss4": -600, "wait": 0.9},

    # LSS5 claw open:  0 → -600  (4 steps of -150)
    {"lss5": -150, "wait": 0.9},
    {"lss5": -300, "wait": 0.9},
    {"lss5": -450, "wait": 0.9},
    {"lss5": -600, "wait": 0.9},

    # ── RETURN TO START ───────────────────────────────────────────────────────
    # Shoulder up first before anything else moves

    # LSS2 shoulder reverse stage 1:  1300  900  (5 steps of -80)
    {"lss2": 1220, "wait": 0.9},
    {"lss2": 1140, "wait": 0.9},
    {"lss2": 1060, "wait": 0.9},
    {"lss2":  980, "wait": 0.9},
    {"lss2":  900, "wait": 0.9},

    # LSS2 shoulder reverse stage 2:  900  0  (5 steps of -180)
    {"lss2":  720, "wait": 0.9},
    {"lss2":  540, "wait": 0.9},
    {"lss2":  360, "wait": 0.9},
    {"lss2":  180, "wait": 0.9},
    {"lss2":    0, "wait": 0.9},

    # LSS3 elbow back:  -900  0  (5 steps of 180)
    {"lss3": -720, "wait": 0.9},
    {"lss3": -540, "wait": 0.9},
    {"lss3": -360, "wait": 0.9},
    {"lss3": -180, "wait": 0.9},
    {"lss3":    0, "wait": 0.9},

    # LSS4 wrist back:  -600  0  (5 steps of 120)
    {"lss4": -480, "wait": 0.9},
    {"lss4": -360, "wait": 0.9},
    {"lss4": -240, "wait": 0.9},
    {"lss4": -120, "wait": 0.9},
    {"lss4":    0, "wait": 0.9},

    # LSS1 base back:  900  -900  (10 steps of -180) — big sweep, keep fine
    {"lss1":  720, "wait": 0.9},
    {"lss1":  180, "wait": 0.9},
    {"lss1": -360, "wait": 0.9},
    {"lss1": -900, "wait": 0.9},

    # ── BACK AT START — claw open, ready for next pickup ─────────────────────
]

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║              END OF SEQUENCES                                            ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


# ── HOME / STARTING POSITION ──────────────────────────────────────────────────
# Matches the starting position from the position test script exactly
HOME = {
    "lss1": -900,   # base rotated to start side
    "lss2":    0,   # shoulder down
    "lss3":    0,   # elbow straight
    "lss4":    0,   # wrist neutral
    "lss5": -600,   # claw open
}


# ── SEQUENCE RUNNER ───────────────────────────────────────────────────────────

class SequenceRunner:
    """Runs a pickup sequence in a background thread so the camera stays live."""

    def __init__(self):
        self._running = False
        self._thread  = None

    @property
    def busy(self):
        return self._running

    def run(self, sequence, servo_map, label="SEQ"):
        if self._running:
            print("[SKIP]  Already running — finish current sequence first.")
            return
        self._thread = threading.Thread(
            target=self._execute,
            args=(sequence, servo_map, label),
            daemon=True,
        )
        self._thread.start()

    def _execute(self, sequence, servo_map, label):
        self._running = True
        print(f"\n[{label}] Starting — {len(sequence)} step(s)")
        for i, step in enumerate(sequence):
            wait  = step.get("wait", 1.2)
            moves = {k: v for k, v in step.items() if k != "wait"}
            for joint, pos in moves.items():
                if joint in servo_map:
                    servo_map[joint].move(pos)
            print(f"[{label}] Step {i+1}/{len(sequence)}: {moves}  (wait {wait}s)")
            time.sleep(wait)
        self._running = False
        print(f"[{label}] Done.\n")


# ── GESTURE CLASSIFIER ────────────────────────────────────────────────────────

def _finger_up(lm, tip, mcp):
    return lm[tip].y < lm[mcp].y

def classify(lm) -> str:
    idx   = _finger_up(lm,  8,  5)
    mid   = _finger_up(lm, 12,  9)
    ring  = _finger_up(lm, 16, 13)
    pinky = _finger_up(lm, 20, 17)
    up    = sum([idx, mid, ring, pinky])

    # Open palm — all 4 fingers extended (replaces fist for home)
    if up == 4:                      return "OPEN"
    # One finger — index only
    if up == 1 and idx:              return "ONE_FINGER"
    # Peace sign — index + middle only
    if up == 2 and idx and mid:      return "PEACE"
    return "UNKNOWN"


# ── CAMERA OVERLAY ────────────────────────────────────────────────────────────

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

GESTURE_LABELS = {
    "OPEN":       "HOME",
    "ONE_FINGER": "PICKUP  item 1",
    "PEACE":      "DROP OFF  item 2",
    "UNKNOWN":    "--",
}

GREEN = (60, 220, 120)
AMBER = (30, 165, 255)
GREY  = (110, 110, 110)

def draw_overlay(frame, gesture, lm_list, busy):
    h, w = frame.shape[:2]

    if lm_list:
        pts = [(int(l.x * w), int(l.y * h)) for l in lm_list]
        for a, b in CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (70, 70, 70), 1)
        for (x, y) in pts:
            cv2.circle(frame, (x, y), 5, (255, 255, 255), -1)
            cv2.circle(frame, (x, y), 5, GREEN, 1)

    if busy:
        label = "RUNNING SEQUENCE..."
        color = AMBER
    else:
        label = GESTURE_LABELS.get(gesture, "--")
        color = GREEN if gesture in ("OPEN", "ONE_FINGER", "PEACE") else GREY

    cv2.rectangle(frame, (0, 0), (w, 55), (0, 0, 0), -1)
    cv2.putText(frame, f"Gesture : {label}", (12, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)

    cv2.rectangle(frame, (0, h - 28), (w, h), (0, 0, 0), -1)
    cv2.putText(frame, "Open palm=HOME   1 finger=Pickup   Peace=Drop off   Q=quit",
                (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (160, 160, 160), 1)


# ── MODEL DOWNLOAD ────────────────────────────────────────────────────────────

def download_model():
    if os.path.exists(MODEL_PATH):
        print(f"[OK]   Model found: {MODEL_PATH}")
        return
    print("[INFO] Downloading hand landmark model (~8 MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("[OK]   Model downloaded.")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    download_model()

    print(f"[INFO] Connecting to LSS bus on {CST_LSS_Port}...")
    lss.initBus(CST_LSS_Port, CST_LSS_Baud)

    myLSS1 = lss.LSS(1)
    myLSS2 = lss.LSS(2)
    myLSS3 = lss.LSS(3)
    myLSS4 = lss.LSS(4)
    myLSS5 = lss.LSS(5)

    servo_map = {
        "lss1": myLSS1,
        "lss2": myLSS2,
        "lss3": myLSS3,
        "lss4": myLSS4,
        "lss5": myLSS5,
    }

    def go_home():
        """Send all joints directly to starting position."""
        for joint, pos in HOME.items():
            servo_map[joint].move(pos)
        print("[HOME]  All joints returning to starting position")

    runner = SequenceRunner()

    print("[INFO] Moving to starting position...")
    go_home()
    time.sleep(3.0)   # give all joints time to reach start before camera opens
    print("[OK]   At starting position.\n")

    base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options   = mp_vision.HandLandmarkerOptions(
        base_options                  = base_opts,
        num_hands                     = 1,
        min_hand_detection_confidence = CONFIDENCE,
        min_hand_presence_confidence  = CONFIDENCE,
        min_tracking_confidence       = CONFIDENCE,
    )
    detector = mp_vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera {CAMERA_INDEX}")
        lss.closeBus()
        return

    print("[INFO] Camera ready. Show gestures:\n")
    print("  Open palm   →  HOME (starting position)")
    print("  One finger  →  Pick up item")
    print("  Peace (V)   →  Drop off item + return to start")
    print("  Q           →  Quit\n")

    last_gesture   = "UNKNOWN"
    last_home_time = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Camera read failed.")
                break

            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = detector.detect(mp_image)

            gesture = "UNKNOWN"
            lm_list = None

            if result.hand_landmarks:
                lm_list = result.hand_landmarks[0]
                gesture = classify(lm_list)
                now     = time.time()

                # Trigger only on rising edge — not while gesture is held
                if gesture != last_gesture:

                    if gesture == "OPEN" and not runner.busy:
                        if now - last_home_time > 1.0:
                            go_home()
                            last_home_time = now

                    elif gesture == "ONE_FINGER" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_1, servo_map, "PICKUP")

                    elif gesture == "PEACE" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_2, servo_map, "DROPOFF")

                last_gesture = gesture
            else:
                last_gesture = "UNKNOWN"

            draw_overlay(frame, gesture, lm_list, runner.busy)
            cv2.imshow("LSS Gesture Arm", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")

    finally:
        print("[INFO] Shutting down safely...")
        go_home()
        time.sleep(2.0)
        cap.release()
        detector.close()
        cv2.destroyAllWindows()
        del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
        lss.closeBus()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()