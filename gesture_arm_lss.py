###############################################################################
# Gesture-Controlled Robot Arm — LSS1 / LSS2 / LSS3
# Dr Oisin Cawley  |  Mar 2026
# Rewritten for MediaPipe 0.10+ (Tasks API — no mp.solutions needed)
#
# FIRST RUN: downloads hand_landmarker.task (~8 MB) automatically.
#
# GESTURES:
#   One finger  (index only)    →  LSS1 rotate LEFT   (hold to keep moving)
#   Peace sign  (index+middle)  →  LSS1 rotate RIGHT  (hold to keep moving)
#   Thumb up                    →  LSS3 elbow UP       (toward 0 / extended)
#   Thumb down                  →  LSS3 elbow DOWN     (toward -1200 / lowest)
#   Fist                        →  HOLD   (all servos freeze where they are)
#   Open palm                   →  HOME   (return all joints to neutral)
#   No hand / unknown           →  nothing sent
#
# JOINT RANGES:
#   LSS1  rotation  : -900  →  0  →  +900   (left ← center → right)
#   LSS2  hinge     : FIXED at -600
#   LSS3  elbow     : -1200 →  0            (-1200=low, 0=extended up)
#
# REQUIRES:
#   pip install mediapipe opencv-python lss
###############################################################################
# Notes:
#   One finger  (index only)    →  LSS1 rotate LEFT   (hold to keep moving) //script to pick up item 1
#   Peace sign  (index+middle)  →  LSS1 rotate RIGHT  (hold to keep moving) //script to pick up item 2 
#   Fist                        →  HOLD   (all servos freeze where they are) //keep same
#   Open palm                   →  HOME   (return all joints to neutral)  //keep as home
#

##########################################################################################
import os
import time
import urllib.request
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

LSS1_STEP = 60      # units per tick for base rotation
LSS3_STEP = 80      # units per tick for elbow

LSS1_MIN, LSS1_MAX = -900,  900
LSS2_FIXED         = -600
LSS3_MIN, LSS3_MAX = -1200,  0

MOVE_INTERVAL = 0.15    # seconds between incremental moves while gesture is held
CONFIDENCE    = 0.75

MODEL_URL  = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
MODEL_PATH = "hand_landmarker.task"
# ─────────────────────────────────────────────────────────────────────────────


def download_model():
    """Download the MediaPipe hand landmark model on first run."""
    if os.path.exists(MODEL_PATH):
        print(f"[OK]   Model found: {MODEL_PATH}")
        return
    print("[INFO] Downloading hand landmark model (~8 MB) ...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[OK]   Saved to {MODEL_PATH}")


# ── GESTURE CLASSIFIER ────────────────────────────────────────────────────────

def _finger_up(lm, tip, mcp):
    """True when fingertip is above the knuckle (y increases downward)."""
    return lm[tip].y < lm[mcp].y

def _thumb_dir(lm):
    """Returns 'UP', 'DOWN', or 'SIDE' for the thumb relative to the wrist."""
    dy = lm[0].y - lm[4].y     # positive → tip above wrist
    dx = abs(lm[4].x - lm[0].x)
    if dx > abs(dy) * 1.2:
        return "SIDE"
    return "UP" if dy > 0.1 else "DOWN"

def classify(lm) -> str:
    """
    lm = list of 21 NormalizedLandmark from MediaPipe Tasks.
    Returns one of: ONE_FINGER, PEACE, THUMB_UP, THUMB_DOWN, FIST, OPEN, UNKNOWN
    """
    idx   = _finger_up(lm,  8,  5)
    mid   = _finger_up(lm, 12,  9)
    ring  = _finger_up(lm, 16, 13)
    pinky = _finger_up(lm, 20, 17)
    up    = sum([idx, mid, ring, pinky])
    thumb = _thumb_dir(lm)

    if up == 4:                     return "OPEN"
    if up == 0 and thumb == "SIDE": return "FIST"
    if up == 0 and thumb == "UP":   return "THUMB_UP"
    if up == 0 and thumb == "DOWN": return "THUMB_DOWN"
    if up == 1 and idx:             return "ONE_FINGER"
    if up == 2 and idx and mid:     return "PEACE"
    return "UNKNOWN"


# ── SERVO STATE ───────────────────────────────────────────────────────────────

class ArmState:
    def __init__(self):
        self.lss1 = 0
        self.lss3 = 0

    def move_lss1(self, delta, servo):
        self.lss1 = max(LSS1_MIN, min(LSS1_MAX, self.lss1 + delta))
        servo.move(self.lss1)

    def move_lss3(self, delta, servo):
        self.lss3 = max(LSS3_MIN, min(LSS3_MAX, self.lss3 + delta))
        servo.move(self.lss3)

    def home(self, s1, s2, s3):
        self.lss1 = 0
        self.lss3 = 0
        s1.move(0)
        s2.move(LSS2_FIXED)
        s3.move(0)


# ── OVERLAY ───────────────────────────────────────────────────────────────────

# Hand bone pairs for drawing the skeleton manually
CONNECTIONS = [
    (0,1),(1,2),(2,3),(3,4),
    (0,5),(5,6),(6,7),(7,8),
    (0,9),(9,10),(10,11),(11,12),
    (0,13),(13,14),(14,15),(15,16),
    (0,17),(17,18),(18,19),(19,20),
    (5,9),(9,13),(13,17),
]

GESTURE_LABELS = {
    "ONE_FINGER": "LSS1  LEFT",
    "PEACE":      "LSS1  RIGHT",
    "THUMB_UP":   "LSS3  UP",
    "THUMB_DOWN": "LSS3  DOWN",
    "FIST":       "HOLD",
    "OPEN":       "HOME",
    "UNKNOWN":    "--",
}

ACTIVE_COLOR   = (60, 220, 120)
INACTIVE_COLOR = (100, 100, 100)

def draw_overlay(frame, gesture, lm_list, state):
    h, w = frame.shape[:2]

    # Draw skeleton
    if lm_list:
        pts = [(int(l.x * w), int(l.y * h)) for l in lm_list]
        for a, b in CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (70, 70, 70), 1)
        for (x, y) in pts:
            cv2.circle(frame, (x, y), 5, (255, 255, 255), -1)
            cv2.circle(frame, (x, y), 5, ACTIVE_COLOR, 1)

    # Gesture label bar (top)
    label = GESTURE_LABELS.get(gesture, "--")
    color = ACTIVE_COLOR if gesture not in ("UNKNOWN", "FIST") else INACTIVE_COLOR
    cv2.rectangle(frame, (0, 0), (w, 52), (0, 0, 0), -1)
    cv2.putText(frame, f"Gesture : {label}", (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

    # Servo position bar (bottom)
    cv2.rectangle(frame, (0, h - 32), (w, h), (0, 0, 0), -1)
    status = (f"LSS1={state.lss1:+5d}   "
              f"LSS2={LSS2_FIXED} (fixed)   "
              f"LSS3={state.lss3:+5d}")
    cv2.putText(frame, status, (12, h - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    download_model()

    # Servos
    print(f"[INFO] Opening LSS bus on {CST_LSS_Port}...")
    lss.initBus(CST_LSS_Port, CST_LSS_Baud)
    myLSS1 = lss.LSS(1)
    myLSS2 = lss.LSS(2)
    myLSS3 = lss.LSS(3)

    state = ArmState()
    print("[INFO] Moving to home position...")
    state.home(myLSS1, myLSS2, myLSS3)
    time.sleep(1.5)
    print("[OK]   Arm homed.")

    # MediaPipe 0.10+ Tasks API
    base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    options   = mp_vision.HandLandmarkerOptions(
        base_options                  = base_opts,
        num_hands                     = 1,
        min_hand_detection_confidence = CONFIDENCE,
        min_hand_presence_confidence  = CONFIDENCE,
        min_tracking_confidence       = CONFIDENCE,
    )
    detector = mp_vision.HandLandmarker.create_from_options(options)

    # Webcam
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open camera index {CAMERA_INDEX}")
        lss.closeBus()
        return

    print("[INFO] Camera open. Show gestures. Press Q to quit.\n")
    print("  One finger  →  LSS1 LEFT")
    print("  Peace (V)   →  LSS1 RIGHT")
    print("  Thumb up    →  LSS3 UP")
    print("  Thumb down  →  LSS3 DOWN")
    print("  Fist        →  HOLD")
    print("  Open palm   →  HOME\n")

    last_move_time = 0
    last_home_time = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] Frame read failed.")
                break

            frame = cv2.flip(frame, 1)
            rgb   = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run hand detection
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result   = detector.detect(mp_image)

            gesture = "UNKNOWN"
            lm_list = None

            if result.hand_landmarks:
                lm_list = result.hand_landmarks[0]   # 21 NormalizedLandmark objects
                gesture = classify(lm_list)
                now     = time.time()

                if gesture == "OPEN" and now - last_home_time > 1.0:
                    state.home(myLSS1, myLSS2, myLSS3)
                    last_home_time = now
                    print("[HOME]  All joints returned to 0")

                elif gesture not in ("FIST", "OPEN", "UNKNOWN"):
                    if now - last_move_time >= MOVE_INTERVAL:
                        if gesture == "ONE_FINGER":
                            state.move_lss1(-LSS1_STEP, myLSS1)
                            print(f"[LSS1]  LEFT  → {state.lss1:+d}")
                        elif gesture == "PEACE":
                            state.move_lss1(+LSS1_STEP, myLSS1)
                            print(f"[LSS1]  RIGHT → {state.lss1:+d}")
                        elif gesture == "THUMB_UP":
                            state.move_lss3(+LSS3_STEP, myLSS3)
                            print(f"[LSS3]  UP    → {state.lss3:+d}")
                        elif gesture == "THUMB_DOWN":
                            state.move_lss3(-LSS3_STEP, myLSS3)
                            print(f"[LSS3]  DOWN  → {state.lss3:+d}")
                        last_move_time = now

                # FIST → hold (no command sent, arm stays put)

            draw_overlay(frame, gesture, lm_list, state)
            cv2.imshow("LSS Gesture Arm  [Q = quit]", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt.")

    finally:
        print("[INFO] Shutting down safely...")
        state.home(myLSS1, myLSS2, myLSS3)
        time.sleep(1)
        cap.release()
        detector.close()
        cv2.destroyAllWindows()
        del myLSS1, myLSS2, myLSS3
        lss.closeBus()
        print("[INFO] Done.")


if __name__ == "__main__":
    main()