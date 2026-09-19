import ctypes
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
SEQUENCE_CLASS_ID = 4
SUPER_G_CLASS_ID = 5

SEQUENCE_ORDER = ["blue", "red", "yellow", "green"]
LOOP_SLEEP_SECONDS = 0.2

# Access Windows native user interface API
user32 = ctypes.windll.user32

# Virtual-Key code for the Middle Mouse Button (scroll wheel press)
VK_MBUTTON = 0x04


def is_middle_click_pressed():
    """Returns True if the mouse wheel button is physically held down."""
    # 0x8000 checks if the most significant bit is set (meaning button is currently down)
    return (user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000) != 0


def fast_click(screen_x, screen_y):
    """Teleports cursor and sends an instant single left click."""
    user32.SetCursorPos(screen_x, screen_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left Mouse Down
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left Mouse Up


def burst_click(screen_x, screen_y, total_clicks=28, tap_gap=0.003):
    """Sends rapid clicks, but cancels immediately if middle mouse button is pressed."""
    user32.SetCursorPos(screen_x, screen_y)
    for _ in range(total_clicks):
        # Emergency check inside the rapid burst
        if is_middle_click_pressed():
            return False

        user32.mouse_event(0x0002, 0, 0, 0, 0)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        if tap_gap > 0:
            time.sleep(tap_gap)
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
            # Emergency Stop Check 1: Start of loop
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 1. Capture the exact game area
            screenshot = sct.grab(GAME_REGION)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 2. Run GPU detection
            results = model.predict(
                source=frame, device=0, conf=0.45, verbose=False
            )
            result = results[0]

            super_g_targets = []
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
                            "is_priority": class_id == 0,
                        }
                    )

            # 4. Action Execution
            executed_super_g = False

            if super_g_targets:
                target = super_g_targets[0]
                completed = burst_click(
                    target["x"], target["y"], total_clicks=28, tap_gap=0.003
                )
                if not completed:
                    print("\n[EMERGENCY STOP] Stopped during Super G burst!")
                    break
                executed_super_g = True

            elif len(sequence_balloons) >= 3:
                for target_color in SEQUENCE_ORDER:
                    if is_middle_click_pressed():
                        break
                    for balloon in sequence_balloons:
                        if balloon["color"] == target_color:
                            fast_click(balloon["x"], balloon["y"])
                            time.sleep(0.04)
                            break

            elif standard_targets:
                standard_targets.sort(
                    key=lambda t: t["is_priority"], reverse=True
                )
                for target in standard_targets:
                    if is_middle_click_pressed():
                        break
                    fast_click(target["x"], target["y"])
                    time.sleep(0.02)

            # Emergency Stop Check 2: After actions
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 5. Visual Preview
            preview = result.plot()
            cv2.imshow("Tap Party Vision Bot", preview)

            # 6. Sleep control
            if not executed_super_g:
                time.sleep(LOOP_SLEEP_SECONDS)
            else:
                time.sleep(0.05)

            # Legacy 'q' key check in case OpenCV preview window has focus
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()