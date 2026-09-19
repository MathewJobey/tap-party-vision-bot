import ctypes
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# 1. Load your best trained YOLO weights
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
# 0: gemini, 1: hazard, 2: safe, 3: safe-pair, 4: sequence, 5: super_g
HAZARD_CLASS_ID = 1
SEQUENCE_CLASS_ID = 4

# Windows low-level mouse controller
user32 = ctypes.windll.user32


def fast_click(screen_x, screen_y):
    """Teleports cursor and sends an instant left click."""
    user32.SetCursorPos(screen_x, screen_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # Left Mouse Down
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # Left Mouse Up


def detect_balloon_color(crop_bgr):
    """Inspects the center pixels of a balloon to determine its color."""
    h, w, _ = crop_bgr.shape
    # Sample the inner 40% of the balloon to avoid the background
    center = crop_bgr[
        int(h * 0.3) : int(h * 0.7), int(w * 0.3) : int(w * 0.7)
    ]

    # If the crop is somehow empty, default to unknown
    if center.size == 0:
        return "unknown"

    # Convert image patch to HSV (Hue, Saturation, Value)
    hsv = cv2.cvtColor(center, cv2.COLOR_BGR2HSV)
    avg_hue = np.median(hsv[:, :, 0])

    # OpenCV Hue scale is 0 to 180
    if 90 <= avg_hue <= 135:
        return "blue"
    elif 40 <= avg_hue < 90:
        return "green"
    elif 15 <= avg_hue < 40:
        return "yellow"
    else:
        return "red"  # Red wraps around 0-15 and 160-180

# The exact order required by the sequence mini-game
SEQUENCE_ORDER = ["blue", "red", "yellow", "green"]

# Sleep duration per frame loop (adjust between 0.10 and 0.18s)
LOOP_SLEEP_SECONDS = 0.2


def run_bot():
    print("\n[BOT ACTIVE] Switch to your browser window!")
    print("Press 'q' in the preview window to STOP.\n")
    time.sleep(2)

    with mss.mss() as sct:
        while True:
            # 1. Capture the exact game area
            screenshot = sct.grab(GAME_REGION)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 2. Run GPU detection (strict confidence to avoid false empty clicks)
            results = model.predict(
                source=frame, device=0, conf=0.45, verbose=False
            )
            result = results[0]

            sequence_balloons = []
            standard_targets = []

            # 3. Categorize detected objects
            for box in result.boxes:
                class_id = int(box.cls[0])

                # Strict Rule: NEVER click hazards
                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2

                global_x = GAME_REGION["left"] + center_x
                global_y = GAME_REGION["top"] + center_y

                # Handle sequence balloons separately
                if class_id == SEQUENCE_CLASS_ID:
                    balloon_crop = frame[y1:y2, x1:x2]
                    color = detect_balloon_color(balloon_crop)
                    sequence_balloons.append(
                        {"x": global_x, "y": global_y, "color": color}
                    )
                else:
                    # Regular scoring balloons
                    standard_targets.append(
                        {
                            "x": global_x,
                            "y": global_y,
                            "is_priority": class_id in (0, 5),  # gemini, super_g
                        }
                    )

            # 4. Action Phase: Handle Sequence Round
            if len(sequence_balloons) >= 3:
                # Click in Blue -> Red -> Yellow -> Green order
                for target_color in SEQUENCE_ORDER:
                    for balloon in sequence_balloons:
                        if balloon["color"] == target_color:
                            fast_click(balloon["x"], balloon["y"])
                            time.sleep(0.04)  # Small gap between sequence taps
                            break

            # 5. Action Phase: Handle Standard Round
            elif standard_targets:
                # Click bonus balloons (super_g, gemini) first
                standard_targets.sort(
                    key=lambda t: t["is_priority"], reverse=True
                )

                for target in standard_targets:
                    fast_click(target["x"], target["y"])
                    time.sleep(0.02)  # Short gap between hits

            # Show live preview
            preview = result.plot()
            cv2.imshow("Tap Party Vision Bot", preview)

            # 6. Raw Loop Sleep: Let balloons pop before re-scanning
            time.sleep(LOOP_SLEEP_SECONDS)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("\n[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()