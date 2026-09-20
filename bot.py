import ctypes
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# 1. Enable Windows High-DPI Awareness so coordinates match physical pixels
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

# 5. Timer Configuration
ROUND_DURATION_SECONDS = 59.0  # Adjust to match your game's total round length (e.g. 60 or 45)
LAST_SECONDS_THRESHOLD = 5.0   # Trigger spam mode when 5 seconds or less remain
NORMAL_LOOP_SLEEP = 0.20       # Calm snapshot pause during standard play

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


def burst_click(x, y, count=28, delay=0.000):
    """Sends 28 rapid clicks for Super G while monitoring emergency stop."""
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
    print("\n[BOT READY] Switch to your browser window!")
    print(">>> Press [MIDDLE MOUSE CLICK] at any time to STOP. <<<\n")
    time.sleep(2)

    game_start_time = None
    spam_mode_announced = False

    with mss.MSS() as sct:
        while True:
            # 1. Emergency stop check
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            now = time.time()

            # 2. Check how much time is left in the round
            is_spam_mode = False
            if game_start_time is not None:
                elapsed = now - game_start_time
                remaining = ROUND_DURATION_SECONDS - elapsed

                if remaining <= LAST_SECONDS_THRESHOLD:
                    is_spam_mode = True
                    if not spam_mode_announced:
                        print(f"\n[SPAM MODE ACTIVATED] Final {LAST_SECONDS_THRESHOLD}s! Clicking everything!")
                        spam_mode_announced = True

            # 3. Capture the exact game region
            screenshot = sct.grab(GAME_REGION)
            frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

            # 4. Run YOLO detection
            results = model.predict(
                source=frame, device=0, conf=0.45, verbose=False
            )
            result = results[0]

            super_g_targets = []
            sequence_balloons = []
            pair_targets = []
            standard_targets = []
            all_non_hazards = []

            # 5. Filter and categorize detected balloons
            for box in result.boxes:
                class_id = int(box.cls[0])

                # Never click hazards under any condition
                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                screen_x = GAME_REGION["left"] + (x1 + x2) // 2
                screen_y = GAME_REGION["top"] + (y1 + y2) // 2

                # Always add non-hazards to the master list
                all_non_hazards.append((screen_x, screen_y))

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

            # 6. Action Execution Branch
            if is_spam_mode:
                # -------------------------------------------------------------
                # FINAL 5 SECONDS: Rapidly click every single non-hazard target
                # -------------------------------------------------------------
                for sx, sy in all_non_hazards:
                    if is_middle_click_pressed():
                        break
                    click(sx, sy)
                    time.sleep(0.000)  # 1ms ultra-rapid spacing

                # In spam mode, do not sleep 0.25s; immediately take the next snapshot
                time.sleep(0.01)

            else:
                # -------------------------------------------------------------
                # STANDARD PLAY: Clean, paced 0.25-second cycle
                # -------------------------------------------------------------
                clicked_something = False

                # Case A: Super G
                if super_g_targets:
                    sx, sy = super_g_targets[0]
                    clicked_something = True
                    if not burst_click(sx, sy):
                        print("\n[EMERGENCY STOP] Stopped during Super G burst!")
                        break

                # Case B: Sequence round
                elif len(sequence_balloons) == 4:
                    for target_color in SEQUENCE_ORDER:
                        if is_middle_click_pressed():
                            break
                        for balloon in sequence_balloons:
                            if balloon["color"] == target_color:
                                click(balloon["x"], balloon["y"])
                                clicked_something = True
                                time.sleep(0.03)
                                break

                # Case C: Safe pairs
                elif len(pair_targets) == 2:
                    click(pair_targets[0][0], pair_targets[0][1])
                    click(pair_targets[1][0], pair_targets[1][1])
                    clicked_something = True

                # Case D: Standard balloons
                elif standard_targets:
                    standard_targets.sort(
                        key=lambda item: item["priority"], reverse=True
                    )
                    for target in standard_targets:
                        if is_middle_click_pressed():
                            break
                        click(target["x"], target["y"])
                        clicked_something = True
                        time.sleep(0.02)

                # Start the countdown timer upon the very first click
                if clicked_something and game_start_time is None:
                    game_start_time = time.time()
                    print("[TIMER STARTED] Round timer is running!")

                # Standard 0.25-second snapshot pause
                time.sleep(NORMAL_LOOP_SLEEP)

    print("\n[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()