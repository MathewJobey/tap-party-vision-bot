import ctypes
import random
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# 1. Load trained YOLO weights
model_path = r"runs/detect/train/weights/best.pt"
print(f"Loading custom model from {model_path}...")
model = YOLO(model_path)

# 2. Game Screen Region
GAME_TUPLE = (650, 100, 620, 915)
GAME_REGION = {
    "left": GAME_TUPLE[0],
    "top": GAME_TUPLE[1],
    "width": GAME_TUPLE[2],
    "height": GAME_TUPLE[3],
}

# 3. Class IDs from data.yaml
HAZARD_CLASS_ID = 1
SAFE_PAIR_CLASS_ID = 3
SEQUENCE_CLASS_ID = 4
SUPER_G_CLASS_ID = 5

SEQUENCE_ORDER = ["blue", "red", "yellow", "green"]
LOOP_SLEEP_SECONDS = 0.15

# Access Windows native user interface API
user32 = ctypes.windll.user32
VK_MBUTTON = 0x04


def is_middle_click_pressed():
    """Returns True if the mouse wheel button is physically held down."""
    return (user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000) != 0


def human_click(screen_x, screen_y, jitter_radius=4):
    """Teleports cursor near target with slight human positional jitter and clicks."""
    # Add slight pixel wobble
    offset_x = screen_x + random.randint(-jitter_radius, jitter_radius)
    offset_y = screen_y + random.randint(-jitter_radius, jitter_radius)

    user32.SetCursorPos(offset_x, offset_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left Mouse Down

    # Human down-to-up contact time (10ms - 18ms)
    time.sleep(random.uniform(0.010, 0.018))
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left Mouse Up


def human_burst_click(
    screen_x, screen_y, total_clicks=28, min_delay=0.038, max_delay=0.052
):
    """Fires 28 humanized taps across ~1.2s with variable rhythm and slight wobble."""
    for _ in range(total_clicks):
        if is_middle_click_pressed():
            return False

        # Apply minor coordinate jitter for each tap in the burst
        wobble_x = screen_x + random.randint(-3, 3)
        wobble_y = screen_y + random.randint(-3, 3)
        user32.SetCursorPos(wobble_x, wobble_y)

        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(random.uniform(0.008, 0.014))
        user32.mouse_event(0x0004, 0, 0, 0, 0)

        # Non-uniform delay between taps (simulates fast finger tapping)
        time.sleep(random.uniform(min_delay, max_delay))

    return True

def detect_balloon_color(crop_bgr):
    """Inspects the center pixels of a balloon to determine its color."""
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
    print("\n[BOT ACTIVE] Switch to your browser window!")
    print(">>> Press [MIDDLE MOUSE CLICK] or 'q' at any time to STOP. <<<\n")
    time.sleep(2)

    with mss.mss() as sct:
        while True:
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 1. Screen capture
            screenshot = sct.grab(GAME_REGION)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 2. Run GPU detection
            results = model.predict(
                source=frame, device=0, conf=0.45, verbose=False
            )
            result = results[0]

            super_g_targets = []
            safe_pair_targets = []
            sequence_balloons = []
            standard_targets = []

            # 3. Categorize detected objects
            for box in result.boxes:
                class_id = int(box.cls[0])

                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                global_x = GAME_REGION["left"] + center_x
                global_y = GAME_REGION["top"] + center_y

                if class_id == SUPER_G_CLASS_ID:
                    super_g_targets.append({"x": global_x, "y": global_y})
                elif class_id == SAFE_PAIR_CLASS_ID:
                    safe_pair_targets.append({"x": global_x, "y": global_y})
                elif class_id == SEQUENCE_CLASS_ID:
                    balloon_crop = frame[y1:y2, x1:x2]
                    color = detect_balloon_color(balloon_crop)
                    sequence_balloons.append(
                        {"x": global_x, "y": global_y, "color": color}
                    )
                else:
                    standard_targets.append(
                        {
                            "x": global_x,
                            "y": global_y,
                            "is_priority": class_id == 0,  # Gemini bonus
                        }
                    )

            # 4. Action Execution
            executed_super_g = False

            # Action 1: Super G with natural burst speed
            if super_g_targets:
                target = super_g_targets[0]
                completed = human_burst_click(target["x"], target["y"], total_clicks=28)
                if not completed:
                    print("\n[EMERGENCY STOP] Stopped during Super G burst!")
                    break
                executed_super_g = True

            # Action 2: Safe-Pair near-simultaneous taps
            elif len(safe_pair_targets) >= 2:
                for target in safe_pair_targets[:2]:
                    if is_middle_click_pressed():
                        break
                    human_click(target["x"], target["y"], jitter_radius=3)
                    # Tiny 20ms human interval between pair touches
                    time.sleep(random.uniform(0.018, 0.026))

            # Action 3: Sequence Mini-game in strict order
            elif len(sequence_balloons) >= 3:
                for target_color in SEQUENCE_ORDER:
                    if is_middle_click_pressed():
                        break
                    for balloon in sequence_balloons:
                        if balloon["color"] == target_color:
                            human_click(balloon["x"], balloon["y"])
                            time.sleep(random.uniform(0.035, 0.050))
                            break

            # Action 4: Standard single targets
            elif standard_targets:
                standard_targets.sort(
                    key=lambda t: t["is_priority"], reverse=True
                )
                for target in standard_targets:
                    if is_middle_click_pressed():
                        break
                    human_click(target["x"], target["y"])
                    time.sleep(random.uniform(0.025, 0.040))

            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 5. Live preview
            preview = result.plot()
            cv2.imshow("Tap Party Vision Bot", preview)

            # 6. Sleep control
            if not executed_super_g:
                time.sleep(LOOP_SLEEP_SECONDS)
            else:
                time.sleep(0.05)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()