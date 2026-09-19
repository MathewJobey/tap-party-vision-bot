import ctypes
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# 1. High-DPI Awareness so coordinates match physical pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# 2. Load trained YOLO weights
model_path = r"runs/detect/train/weights/best.pt"
print(f"Loading custom model from {model_path}...")
model = YOLO(model_path)

# 3. Game Screen Region
GAME_REGION = {
    "left": 650,
    "top": 100,
    "width": 620,
    "height": 915,
}

# 4. Class IDs from data.yaml
GEMINI_CLASS_ID = 0
HAZARD_CLASS_ID = 1
SAFE_CLASS_ID = 2
SAFE_PAIR_CLASS_ID = 3
SEQUENCE_CLASS_ID = 4
SUPER_G_CLASS_ID = 5

SEQUENCE_ORDER = ["blue", "red", "yellow", "green"]

# Access Windows user interface API
user32 = ctypes.windll.user32
VK_MBUTTON = 0x04  # Middle mouse button code


def is_middle_click_pressed():
    """Returns True if the mouse wheel button is physically held down."""
    return (user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000) != 0


def click(x, y):
    """Sends a single direct click to the target coordinates."""
    user32.SetCursorPos(x, y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left down
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left up


def burst_click(x, y, count=28, delay=0.035):
    """Sends 28 rapid clicks for Super G while monitoring the emergency stop."""
    user32.SetCursorPos(x, y)
    for _ in range(count):
        if is_middle_click_pressed():
            return False
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(delay)
    return True

def get_balloon_color(crop_bgr):
    """Inspects the center of a balloon crop to identify its color via HSV."""
    h, w, _ = crop_bgr.shape
    center = crop_bgr[
        int(h * 0.3) : int(h * 0.7), int(w * 0.3) : int(w * 0.7)
    ]

    if center.size == 0:
        return "unknown"

    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    avg_hue = np.median(hsv[:, :, 0])

    if 90 <= avg_hue <= 135:
        return "blue"
    elif 40 <= avg_hue < 90:
        return "green"
    elif 15 <= avg_hue < 40:
        return "yellow"
    else:
        return "red"

def run_bot():
    print("\n[HEADLESS BOT ACTIVE] Switch to your browser window!")
    print(">>> Press [MIDDLE MOUSE CLICK] at any time to STOP. <<<\n")
    time.sleep(2)

    frame_counter = 0

    # Using mss.MSS() resolves the deprecation warning
    with mss.MSS() as sct:
        while True:
            # 1. Emergency stop check
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            frame_counter += 1

            # 2. Capture the exact game region
            screenshot = sct.grab(GAME_REGION)
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

            # 3. Run YOLO detection
            results = model.predict(
                source=frame, device=0, conf=0.45, verbose=False
            )
            result = results[0]

            super_g_targets = []
            sequence_balloons = []
            pair_targets = []
            standard_targets = []

            # 4. Sort detected items (strictly ignore hazards)
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                screen_x = GAME_REGION["left"] + (x1 + x2) // 2
                screen_y = GAME_REGION["top"] + (y1 + y2) // 2

                if class_id == SUPER_G_CLASS_ID:
                    super_g_targets.append((screen_x, screen_y))
                elif class_id == SEQUENCE_CLASS_ID:
                    crop = frame[y1:y2, x1:x2]
                    color = get_balloon_color(crop)
                    sequence_balloons.append(
                        {"x": screen_x, "y": screen_y, "color": color}
                    )
                elif class_id == SAFE_PAIR_CLASS_ID:
                    pair_targets.append((screen_x, screen_y))
                else:
                    standard_targets.append(
                        {
                            "x": screen_x,
                            "y": screen_y,
                            "priority": class_id == GEMINI_CLASS_ID,
                        }
                    )

            # 5. Action Execution
            clicked_count = 0

            # Case A: Super G
            if super_g_targets:
                sx, sy = super_g_targets[0]
                if not burst_click(sx, sy):
                    print("\n[EMERGENCY STOP] Stopped during Super G burst!")
                    break
                clicked_count += 28

            # Case B: Sequence round (exactly 4 balloons found)
            elif len(sequence_balloons) == 4:
                for target_color in SEQUENCE_ORDER:
                    if is_middle_click_pressed():
                        break
                    for balloon in sequence_balloons:
                        if balloon["color"] == target_color:
                            click(balloon["x"], balloon["y"])
                            clicked_count += 1
                            time.sleep(0.03)
                            break

            # Case C: Safe pairs (exactly 2 balloons found)
            elif len(pair_targets) == 2:
                click(pair_targets[0][0], pair_targets[0][1])
                click(pair_targets[1][0], pair_targets[1][1])
                clicked_count += 2

            # Case D: Standard balloons
            elif standard_targets:
                standard_targets.sort(
                    key=lambda item: item["priority"], reverse=True
                )
                for target in standard_targets:
                    if is_middle_click_pressed():
                        break
                    click(target["x"], target["y"])
                    clicked_count += 1
                    time.sleep(0.02)

            # Lightweight console heartbeat (every 4 frames ~= 1 second)
            if frame_counter % 4 == 0:
                print(f"[RUNNING] Frame {frame_counter} | Clicks: {clicked_count}")

            # Check emergency stop after clicking
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 6. Fixed 0.25-second cadence
            time.sleep(0.25)

    print("\n[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()