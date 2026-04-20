# Gesture-Controlled Robot Arm

Control a Lynxmotion Smart Servo arm using hand gestures detected through a laptop webcam. No keyboard input needed during operation.

**Demo:** https://www.youtube.com/shorts/da9gX9PGN7k

---

## Requirements

- Python 3.11 or higher
- Windows (serial port configured as COM7)
- Lynxmotion Smart Servo arm
- Webcam (built-in laptop camera works fine)

---

## Installation

**1. Clone the repo**

```bash
git clone https://github.com/JakePowellLangstaff/robot_arm_code-
cd robot_arm_code-
```

**2. Create a virtual environment (recommended)**

```bash
python -m venv robot_env
robot_env\Scripts\activate
```

**3. Install dependencies**

```bash
pip install mediapipe opencv-python
```

> `lss` and `lss_const` are not on PyPI — they are already included in this repo as `lss.py` and `lss_const.py`. No extra install needed.

**4. Download the MediaPipe model**

The hand landmark model (~8 MB) downloads automatically on first run. If you want to download it manually:

```
https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
```

Place it in the same folder as the script.

---

## Run

```bash
python gesture_arm_lssv3.py
```

The arm moves to its home position on launch, then waits for gestures.

---

## Gestures

| Gesture | Action |
|---|---|
| One finger (index only) | Pick up item |
| Peace sign (index + middle) | Drop off item + auto return to start |
| Open palm (all fingers) | Emergency home |
| Q (keyboard) | Quit |

---

## Configuration

Edit these values at the top of `gesture_arm_lssv3.py`:

```python
CST_LSS_Port = "COM7"   # change to match your serial port
CAMERA_INDEX = 0        # change if using an external webcam
CONFIDENCE   = 0.75     # lower this if detection is dropping out
```

---

## Joint ranges

| Joint | Role | Safe range |
|---|---|---|
| LSS1 | Base rotation | -900 to +900 |
| LSS2 | Shoulder | 0 to 1300 (positive = up) |
| LSS3 | Elbow | 0 to -900 (negative = down) |
| LSS4 | Wrist | 0 to -800 (negative = down) |
| LSS5 | Claw | -600 (open) to 0 (closed) |

---

## File structure

```
robot_arm_code-/
├── gesture_arm_lssv3.py     # main script — run this
├── lss.py                   # LSS serial library
├── lss_const.py             # LSS constants
├── hand_landmarker.task     # MediaPipe model (auto-downloaded)
├── test_position1_2.py      # position test script
├── test_joints.py           # individual joint test
├── test_claw.py             # claw test
└── camera.py                # webcam check
```

---

## Built with

- [MediaPipe](https://github.com/google-ai-edge/mediapipe) — hand landmark detection
- [OpenCV](https://opencv.org/) — webcam capture and overlay
- [LSS Python Library](https://github.com/Lynxmotion/LSS_Library_Python) — servo communication
- Python `threading` — keeps camera live during arm movement
