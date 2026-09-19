import ctypes
import math
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# 1. Model Checkpoint
model_path = r"runs/detect/train/weights/best.pt"
print(f"Loading custom model from {model_path}...")
model = YOLO(model_path)

# 2. Game Screen Coordinates: (left, top, width, height)
GAME_TUPLE = (650, 100, 620, 915)
GAME_REGION = {
    "left": GAME_TUPLE[0],
    "top": GAME_TUPLE[1],
    "width": GAME_TUPLE[2],
    "height": GAME_TUPLE[3],
}

# 3. Class Index Definitions from data.yaml
# 0: gemini, 1: hazard, 2: safe, 3: safe-pair, 4: sequence, 5: super_g
HAZARD_CLASS_ID = 1

# Higher priority number means clicked first
CLASS_PRIORITY = {
    5: 10,  # super_g (highest value)
    0: 9,  # gemini
    4: 8,  # sequence
    3: 5,  # safe-pair
    2: 4,  # safe
}

# Access Windows native mouse controller
user32 = ctypes.windll.user32


def fast_click(screen_x, screen_y):
    """Moves cursor and sends an instant left click."""
    user32.SetCursorPos(screen_x, screen_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)  # Mouse Down
    user32.mouse_event(0x0004, 0, 0, 0, 0)  # Mouse Up

# List holding past clicks: [(x, y, timestamp), ...]
recent_clicks = []

# Minimum time to ignore the same area (pop animation duration)
CLICK_COOLDOWN_SECONDS = 0.25

# Radius around a click to consider "the same balloon" (in pixels)
MIN_DISTANCE_PIXELS = 45


def is_already_clicked(target_x, target_y, current_time):
    """Checks if target coordinates are too close to a balloon clicked recently."""
    global recent_clicks

    # Purge old clicks outside the cooldown window
    recent_clicks = [
        click
        for click in recent_clicks
        if (current_time - click[2]) < CLICK_COOLDOWN_SECONDS
    ]

    # Check distance against active cooldown spots
    for prev_x, prev_y, _ in recent_clicks:
        distance = math.hypot(target_x - prev_x, target_y - prev_y)
        if distance < MIN_DISTANCE_PIXELS:
            return True  # Area is still cooling down

    return False

def run_bot():
    print("\n[BOT READY] Switch to your browser window!")
    print("Press 'q' in the preview window to STOP the bot safely.\n")
    time.sleep(2)

    with mss.mss() as sct:
        while True:
            # Capture game area
            screenshot = sct.grab(GAME_REGION)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # Run GPU detection
            results = model.predict(
                source=frame, device=0, conf=0.40, verbose=False
            )
            result = results[0]

            now = time.time()
            candidates = []

            # Gather all non-hazard targets
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                local_cx = int((x1 + x2) / 2)
                local_cy = int((y1 + y2) / 2)

                global_x = GAME_REGION["left"] + local_cx
                global_y = GAME_REGION["top"] + local_cy

                # Ignore balloon if we just popped this spot
                if is_already_clicked(global_x, global_y, now):
                    continue

                priority = CLASS_PRIORITY.get(class_id, 0)
                candidates.append(
                    {"x": global_x, "y": global_y, "priority": priority}
                )

            # Sort targets so best balloons are clicked first
            candidates.sort(key=lambda item: item["priority"], reverse=True)

            # Execute clicks on valid candidates
            for target in candidates:
                fast_click(target["x"], target["y"])
                recent_clicks.append((target["x"], target["y"], time.time()))
                time.sleep(
                    0.015
                )  # 15ms buffer so browser registers distinct taps

            # Live preview window
            preview = result.plot()
            cv2.imshow("Tap Party Vision Bot", preview)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("\n[BOT STOPPED] Clean exit.")


if __name__ == "__main__":
    run_bot()