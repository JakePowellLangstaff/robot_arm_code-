###############################################################################
# Gesture-Controlled Robot Arm — LSS1–LSS5
# Dr Oisin Cawley  |  Mar 2026
# MediaPipe 0.10+ (Tasks API)
#
# GESTURES:
#   One finger  (index only)   →  PICKUP_SEQUENCE_1  (object directly in front)
#   Peace sign  (index+middle) →  PICKUP_SEQUENCE_2  (lab partner to fill in)
#   Open palm                  →  HOME  (all joints to neutral)
#
# JOINT RANGES:
#   LSS1  base rotation : 0 straight | - right | + left
#   LSS2  shoulder      : 0 up       | -900/+900 parallel with ground
#   LSS3  elbow         : 0 straight | -850 lowest
#   LSS4  wrist         : 0 lowest   | -850 straight out from arm
#   LSS5  claw          : 0 closed   | positive = open
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
# ║            LAB PARTNER — EDIT YOUR SEQUENCES HERE                        ║
# ╠═══════════════════════════════════════════════════════════════════════════╣
# ║  Each step is a dict of joints to move + "wait" seconds after the move.  ║
# ║  Only include the joints changing in that step — omit the rest.          ║
# ║                                                                           ║
# ║  RANGES:                                                                  ║
# ║    lss1  base     :   0 straight | - right    | + left                   ║
# ║    lss2  shoulder :   0 up       | -900/+900  | parallel ground          ║
# ║    lss3  elbow    :   0 straight | -850       | lowest                   ║
# ║    lss4  wrist    :   0 lowest   | -850       | straight out             ║
# ║    lss5  claw     :   0 closed   | +800       | fully open               ║
# ╚═══════════════════════════════════════════════════════════════════════════╝

PICKUP_SEQUENCE_1 = [
    # ── Pick up object directly in front ─────────────────────────────────────
    # Step 1: open claw and raise arm to approach height
    {"lss1":    0, "lss2": -300, "lss3": -200, "lss4": -600, "lss5": 800, "wait": 1.2},

    # Step 2: lower arm down toward object
    {"lss2": -600, "lss3": -600, "lss4": -400, "wait": 1.0},

    # Step 3: extend forward to reach object
    {"lss3": -750, "lss4": -200, "wait": 0.8},

    # Step 4: close claw to grab
    {"lss5": 0, "wait": 0.7},

    # Step 5: lift arm back up with object
    {"lss2": -200, "lss3": -200, "lss4": -600, "wait": 1.0},

    # Step 6: return to home
    {"lss1": 0, "lss2": 0, "lss3": 0, "lss4": 0, "lss5": 0, "wait": 1.0},
]

PICKUP_SEQUENCE_2 = [
    # ── Lab partner: fill in positions for item 2 ────────────────────────────
    # Step 1: ...
    {"lss1": 0, "lss2": 0, "lss3": 0, "lss4": 0, "lss5": 800, "wait": 1.0},
    # Step 2: ...
    {"lss1": 0, "lss2": 0, "lss3": 0, "lss4": 0, "lss5":   0, "wait": 1.0},
    # Step 3: return home
    {"lss1": 0, "lss2": 0, "lss3": 0, "lss4": 0, "lss5":   0, "wait": 1.0},
]

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║            END OF LAB PARTNER SECTION                                    ║
# ╚═══════════════════════════════════════════════════════════════════════════╝


# ── SEQUENCE RUNNER ───────────────────────────────────────────────────────────

class SequenceRunner:
    """Runs a pickup sequence in a background thread so the camera stays live."""

    def __init__(self):
        self._running = False
        self._thread  = None

    @property
    def busy(self):
        return self._running

    def run(self, sequence, servos, label="SEQ"):
        if self._running:
            print(f"[SKIP]  Sequence already running.")
            return
        self._thread = threading.Thread(
            target=self._execute,
            args=(sequence, servos, label),
            daemon=True,
        )
        self._thread.start()

    def _execute(self, sequence, servos, label):
        s1, s2, s3, s4, s5 = servos
        self._running = True
        print(f"[{label}] Starting — {len(sequence)} step(s)")

        servo_map = {"lss1": s1, "lss2": s2, "lss3": s3, "lss4": s4, "lss5": s5}

        for i, step in enumerate(sequence):
            wait = step.get("wait", 0.5)
            moves = {k: v for k, v in step.items() if k != "wait"}

            for joint, pos in moves.items():
                if joint in servo_map:
                    servo_map[joint].move(pos)

            print(f"[{label}] Step {i+1}: {moves}  →  wait {wait}s")
            time.sleep(wait)

        self._running = False
        print(f"[{label}] Complete.")


# ── ARM STATE ─────────────────────────────────────────────────────────────────

class ArmState:
    def __init__(self):
        self.lss1 = 0

    def home(self, servos):
        self.lss1 = 0
        s1, s2, s3, s4, s5 = servos
        s1.move(0)
        s2.move(0)
        s3.move(0)
        s4.move(0)
        s5.move(0)


# ── GESTURE CLASSIFIER ────────────────────────────────────────────────────────

def _finger_up(lm, tip, mcp):
    return lm[tip].y < lm[mcp].y

def classify(lm) -> str:
    idx   = _finger_up(lm,  8,  5)
    mid   = _finger_up(lm, 12,  9)
    ring  = _finger_up(lm, 16, 13)
    pinky = _finger_up(lm, 20, 17)
    up    = sum([idx, mid, ring, pinky])

    if up == 4:                 return "OPEN"
    if up == 1 and idx:         return "ONE_FINGER"
    if up == 2 and idx and mid: return "PEACE"
    return "UNKNOWN"


# ── OVERLAY ───────────────────────────────────────────────────────────────────

CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

GESTURE_LABELS = {
    "ONE_FINGER": "PICKUP item 1",
    "PEACE":      "PICKUP item 2",
    "OPEN":       "HOME",
    "UNKNOWN":    "--",
}

GREEN = (60, 220, 120)
AMBER = (40, 180, 220)
GREY  = (100, 100, 100)

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
        color = GREEN if gesture in ("ONE_FINGER", "PEACE", "OPEN") else GREY

    cv2.rectangle(frame, (0, 0), (w, 52), (0, 0, 0), -1)
    cv2.putText(frame, f"Gesture : {label}", (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)


# ── MODEL DOWNLOAD ────────────────────────────────────────────────────────────

def download_model():
    if os.path.exists(MODEL_PATH):
        print(f"[OK]   Model found: {MODEL_PATH}")
        return
    print("[INFO] Downloading hand landmark model (~8 MB)...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[OK]   Saved to {MODEL_PATH}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    download_model()

    print(f"[INFO] Opening LSS bus on {CST_LSS_Port}...")
    lss.initBus(CST_LSS_Port, CST_LSS_Baud)
    myLSS1 = lss.LSS(1)
    myLSS2 = lss.LSS(2)
    myLSS3 = lss.LSS(3)
    myLSS4 = lss.LSS(4)
    myLSS5 = lss.LSS(5)
    servos = (myLSS1, myLSS2, myLSS3, myLSS4, myLSS5)

    state  = ArmState()
    runner = SequenceRunner()

    print("[INFO] Homing arm...")
    state.home(servos)
    time.sleep(1.5)
    print("[OK]   Arm homed.\n")

    # MediaPipe Tasks API
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
        print(f"[ERROR] Cannot open camera index {CAMERA_INDEX}")
        lss.closeBus()
        return

    print("[INFO] Camera open. Show gestures. Press Q to quit.\n")
    print("  One finger  →  Pickup item 1 (object in front)")
    print("  Peace (V)   →  Pickup item 2")
    print("  Open palm   →  HOME\n")

    last_trigger   = "UNKNOWN"
    last_home_time = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame read failed.")
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

                # Fire only on the rising edge of a new gesture
                if gesture != last_trigger:
                    if gesture == "ONE_FINGER" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_1, servos, "ITEM-1")

                    elif gesture == "PEACE" and not runner.busy:
                        runner.run(PICKUP_SEQUENCE_2, servos, "ITEM-2")

                    elif gesture == "OPEN" and not runner.busy and now - last_home_time > 1.0:
                        state.home(servos)
                        last_home_time = now
                        print("[HOME]  All joints → 0")

                last_trigger = gesture
            else:
                last_trigger = "UNKNOWN"

            draw_overlay(frame, gesture, lm_list, runner.busy)
            cv2.imshow("LSS Gesture Arm  [Q = quit]", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt.")

    finally:
        print("[INFO] Shutting down safely...")
        state.home(servos)
        time.sleep(1)
        cap.release()
        detector.close()
        cv2.destroyAllWindows()
        del myLSS1, myLSS2, myLSS3, myLSS4, myLSS5
        lss.closeBus()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()