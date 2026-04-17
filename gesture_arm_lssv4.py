###############################################################################
# Gesture-Controlled Robot Arm — LSS1–LSS5
# Dr Oisin Cawley  |  Mar 2026
# MediaPipe 0.10+ (Tasks API)
#
# GESTURES:
#   Fist                       →  HOME  (all joints return to neutral)
#   One finger (index only)    →  PICKUP_SEQUENCE_1  (pick up item 1)
#   Peace sign (index+middle)  →  PICKUP_SEQUENCE_2  (pick up item 2)
#
# CONFIRMED JOINT RANGES:
#   LSS1  base      :  0=straight  | -=right       | +=left
#   LSS2  shoulder  :  0=up        | -900=parallel with ground
#   LSS3  elbow     :  0=straight  | -850=lowest
#   LSS4  wrist     :  0=lowest    | -850=straight out from arm
#   LSS5  claw      :  0=closed    | 600=fully open  ← CONFIRMED
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


# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║              LAB PARTNER — EDIT SEQUENCES HERE                           ║
# ╠═══════════════════════════════════════════════════════════════════════════╣
# ║  CONFIRMED RANGES:                                                        ║
# ║    lss1  base     :  0 straight | - right  | + left                      ║
# ║    lss2  shoulder :  0 up       | -900 parallel with ground              ║
# ║    lss3  elbow    :  0 straight | -850 lowest (bend inward)              ║
# ║    lss4  wrist    :  0 lowest   | -850 straight out from arm             ║
# ║    lss5  claw     :  0 closed   | 600 fully open  ← CONFIRMED            ║
# ║                                                                           ║
# ║  Arm HOLDS at end of each sequence — make a FIST to return home          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

PICKUP_SEQUENCE_1 = [
    # ── Item 1 ───────────────────────────────────────────────────────────────

    # Step 1: open claw fully
    {"lss5": 600, "wait": 1.2},

    # Step 2: swing base, lift shoulder to safe travel height
    {"lss1": -600, "lss2": -200, "lss3": -100, "lss4": -750, "wait": 2.5},

    # Step 3: start rotating shoulder down and inward
    {"lss2": -550, "lss3": -350, "lss4": -600, "wait": 2.0},

    # Step 4: shoulder pushing toward parallel, elbow folding in
    {"lss2": -750, "lss3": -600, "lss4": -400, "wait": 2.0},

    # Step 5: shoulder near parallel, elbow bent hard inward
    {"lss2": -850, "lss3": -780, "lss4": -200, "wait": 2.0},

    # Step 6: final depth — elbow at max, wrist nearly flat to table
    {"lss3": -840, "lss4": -80, "wait": 2.0},

    # Step 7: close claw gradually (600 → 400 → 200 → 0)
    {"lss5": 400, "wait": 0.7},
    {"lss5": 200, "wait": 0.7},
    {"lss5":   0, "wait": 1.0},

    # Step 8: lift elbow to clear table with item
    {"lss3": -550, "lss4": -400, "wait": 2.0},

    # ── HOLDS HERE — make a FIST to return home ───────────────────────────────
]

PICKUP_SEQUENCE_2 = [
    # ── Item 2 ───────────────────────────────────────────────────────────────

    # Step 1: open claw fully
    {"lss5": 600, "wait": 1.2},

    # Step 2: swing base, lift shoulder to safe travel height
    {"lss1": -500, "lss2": -200, "lss3": -100, "lss4": -750, "wait": 2.5},

    # Step 3: start rotating shoulder down and inward
    {"lss2": -550, "lss3": -350, "lss4": -600, "wait": 2.0},

    # Step 4: shoulder pushing toward parallel, elbow folding in
    {"lss2": -750, "lss3": -600, "lss4": -400, "wait": 2.0},

    # Step 5: shoulder near parallel, elbow bent hard inward
    {"lss2": -850, "lss3": -780, "lss4": -200, "wait": 2.0},

    # Step 6: final depth — elbow at max, wrist nearly flat to table
    {"lss3": -840, "lss4": -80, "wait": 2.0},

    # Step 7: close claw gradually (600 → 400 → 200 → 0)
    {"lss5": 400, "wait": 0.7},
    {"lss5": 200, "wait": 0.7},
    {"lss5":   0, "wait": 1.0},

    # Step 8: lift elbow to clear table with item
    {"lss3": -550, "lss4": -400, "wait": 2.0},

    # ── HOLDS HERE — make a FIST to return home ───────────────────────────────
]

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║              END OF LAB PARTNER SECTION                                  ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


# ── HOME POSITION ─────────────────────────────────────────────────────────────
HOME = {
    "lss1":    0,     # base centered
    "lss2": -200,     # shoulder mostly upright
    "lss3": -150,     # elbow gently bent
    "lss4": -700,     # wrist raised — clearly away from table
    "lss5":    0,     # claw closed
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
            wait  = step.get("wait", 0.5)
            moves = {k: v for k, v in step.items() if k != "wait"}
            for joint, pos in moves.items():
                if joint in servo_map:
                    servo_map[joint].move(pos)
            print(f"[{label}] Step {i+1}/{len(sequence)}: {moves}  (wait {wait}s)")
            time.sleep(wait)
        self._running = False
        print(f"[{label}] Done — make a FIST to go home.\n")


# ── GESTURE CLASSIFIER ────────────────────────────────────────────────────────

def _finger_up(lm, tip, mcp):
    return lm[tip].y < lm[mcp].y

def _thumb_side(lm):
    dy = abs(lm[0].y - lm[4].y)
    dx = abs(lm[4].x - lm[0].x)
    return dx > dy * 1.2

def classify(lm) -> str:
    idx   = _finger_up(lm,  8,  5)
    mid   = _finger_up(lm, 12,  9)
    ring  = _finger_up(lm, 16, 13)
    pinky = _finger_up(lm, 20, 17)
    up    = sum([idx, mid, ring, pinky])

    if up == 0 and _thumb_side(lm):  return "FIST"
    if up == 1 and idx:              return "ONE_FINGER"
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
    "FIST":       "HOME",
    "ONE_FINGER": "PICKUP  item 1",
    "PEACE":      "PICKUP  item 2",
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
        color = GREEN if gesture in ("FIST", "ONE_FINGER", "PEACE") else GREY

    cv2.rectangle(frame, (0, 0), (w, 55), (0, 0, 0), -1)
    cv2.putText(frame, f"Gesture : {label}", (12, 34),
                cv2.FONT_HERSHEY_SIMPLEX, 0.85, color, 2)

    cv2.rectangle(frame, (0, h - 28), (w, h), (0, 0, 0), -1)
    cv2.putText(frame, "Fist=HOME   1 finger=Item1   Peace=Item2   Q=quit",
                (10, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 160, 160), 1)


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
        for joint, pos in HOME.items():
            servo_map[joint].move(pos)
        print("[HOME]  All joints returning to rest position")

    runner = SequenceRunner()

    print("[INFO] Homing arm...")
    go_home()
    time.sleep(2.0)
    print("[OK]   Arm at home.\n")

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
    print("  Fist        →  HOME")
    print("  One finger  →  Pickup item 1")
    print("  Peace (V)   →  Pickup item 2")
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

                if gesture != last_gesture:
                    if gesture == "FIST" and not runner.busy:
                        if now - last_home_time > 1.0:
                            go_home()
                            last_home_time = now

                    elif gesture == "ONE_FINGER" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_1, servo_map, "ITEM-1")

                    elif gesture == "PEACE" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_2, servo_map, "ITEM-2")

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
        time.sleep(1.5)
        cap.release()
        detector.close()
        cv2.destroyAllWindows()
        del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
        lss.closeBus()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()
