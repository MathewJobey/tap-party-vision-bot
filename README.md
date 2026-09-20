# 🎈 Tap Party Vision Bot

> I don't have esports-tier reaction times, but top 5 on the leaderboard gets a Google Pixel 11 series phone. So naturally, I trained an AI to play for me.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?logo=yolo&logoColor=black)](https://github.com/ultralytics/ultralytics)
[![Roboflow](https://img.shields.io/badge/Dataset-Roboflow-6706CE?logo=roboflow&logoColor=white)](https://universe.roboflow.com/mathew-jobey/tap-party/dataset/2)

---

## 🍿 Demo

| In-Game Bot Action | YOLO Detection |
| :---: | :---: |
| ![Gameplay Demo](assets/demo.gif) | ![YOLO Preview](assets/yolo_detection.png) |

*(Drop your recording into `assets/demo.gif` and detection snapshot into `assets/yolo_detection.png`)*

---

## 💡 The Pivot: OpenCV ➔ YOLOv8

I initially tried building this with pure **OpenCV template matching**. That crashed and burned quickly:
- Balloons float at different speeds, rescale, and overlap each other.
- Subtle in-game lighting and particle effects broke traditional contour and template checks.
- Result: Tons of missed clicks and dead combo multipliers.

To fix it, I captured gameplay frames, annotated them on **Roboflow**, and trained a custom **YOLOv8s** model on an RTX 3050 GPU. Now, the bot actually understands spatial objects in real time (<10ms per frame) rather than guessing pixels.

---

## 🎯 Game Logic & Classes

The model identifies 6 custom classes:

| Class | In-Game Target | Bot Strategy |
| :---: | :--- | :--- |
| `0` | `gemini` | High-value bonus; prioritized in click queues. |
| `1` | `hazard` | **Hard blacklisted.** Kept at a safe distance buffer to save combo multipliers. |
| `2` | `safe` | Standard scoring balloons; single-tapped. |
| `3` | `safe-pair` | Popped back-to-back within milliseconds to register as a dual-touch. |
| `4` | `sequence` | HSV hue analysis pops them in strict order: **Blue ➔ Red ➔ Yellow ➔ Green**. |
| `5` | `super_g` | Fires a rapid, hardware-level burst of 28 consecutive taps. |

---

## 🛠️ Tech Stack

- **Screen Capture:** `mss` (captures the game canvas in ~2ms).
- **Vision:** Ultralytics `YOLOv8s` + OpenCV HSV analysis for sequence colors.
- **Inputs:** Low-level Windows `user32.dll` via `ctypes` (direct hardware cursor teleportation & clicks).
- **Kill-Switch:** Physical emergency stop bound to the **Middle Mouse Button (`VK_MBUTTON`)** to halt instantly without Alt-Tabbing.

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone [https://github.com/mathewjobey/tap-party-vision-bot.git](https://github.com/mathewjobey/tap-party-vision-bot.git)
cd tap-party-vision-bot

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt