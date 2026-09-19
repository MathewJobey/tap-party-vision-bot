import ctypes
import math
import random
import time
import cv2
import mss
import numpy as np
from ultralytics import YOLO

# Force Windows into Per-Monitor DPI Awareness
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

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
GEMINI_CLASS_ID = 0
HAZARD_CLASS_ID = 1
SAFE_CLASS_ID = 2
SAFE_PAIR_CLASS_ID = 3
SEQUENCE_CLASS_ID = 4
SUPER_G_CLASS_ID = 5

SEQUENCE_ORDER = ["blue", "red", "yellow", "green"]

# Access Windows native user interface API
user32 = ctypes.windll.user32
VK_MBUTTON = 0x04

# Multiplier Protection Ledger
recent_clicks = []
POPPED_COOLDOWN_SECONDS = 0.30
MIN_BALLOON_DISTANCE = 40
HAZARD_BUFFER_PX = 34

# End-Game Swarm Override Settings
SWARM_OVERRIDE_THRESHOLD = 10  # Minimum green balloons to trigger full override
SWARM_TAP_DELAY = 0.005       # 8ms rapid-fire tap spacing during swarms
SWARM_LOOP_DELAY = 0.02      # 10ms frame loop delay during swarms
NORMAL_LOOP_DELAY = 0.02     # 40ms frame loop delay during standard rounds


def is_middle_click_pressed():
    """Returns True if the mouse wheel button is physically held down."""
    return (user32.GetAsyncKeyState(VK_MBUTTON) & 0x8000) != 0


def is_spot_on_cooldown(target_x, target_y, current_time):
    """Checks if this location is still cooling down from a recent pop."""
    global recent_clicks
    recent_clicks = [c for c in recent_clicks if c[2] > current_time]
    for px, py, _ in recent_clicks:
        if math.hypot(target_x - px, target_y - py) < MIN_BALLOON_DISTANCE:
            return True
    return False


def flow_click(screen_x, screen_y, jitter_radius=2):
    """Clean click for standard play with natural sub-pixel variance."""
    off_x = screen_x + random.randint(-jitter_radius, jitter_radius)
    off_y = screen_y + random.randint(-jitter_radius, jitter_radius)

    user32.SetCursorPos(off_x, off_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(random.uniform(0.007, 0.011))
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def frenzy_tap(screen_x, screen_y):
    """Machine-gun click for the end-game swarm with zero hold delay."""
    off_x = screen_x + random.randint(-3, 3)
    off_y = screen_y + random.randint(-3, 3)
    user32.SetCursorPos(off_x, off_y)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)


def burst_click(screen_x, screen_y, total_clicks=28, tap_gap=0.038):
    """Fires 28 taps on Super G paced so every single tap registers."""
    user32.SetCursorPos(screen_x, screen_y)
    for _ in range(total_clicks):
        if is_middle_click_pressed():
            return False
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.006)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        if tap_gap > 0:
            time.sleep(tap_gap)
    return True

def detect_balloon_color(crop_bgr):
    """Inspects the center pixels of a balloon to classify color via HSV."""
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


def sort_targets_by_flow(targets):
    """Orders balloons by shortest distance so the mouse sweeps across the screen."""
    if not targets:
        return []

    ordered = []
    current = targets.pop(0)
    ordered.append(current)

    while targets:
        nearest_index = min(
            range(len(targets)),
            key=lambda i: math.hypot(
                current["x"] - targets[i]["x"], current["y"] - targets[i]["y"]
            ),
        )
        current = targets.pop(nearest_index)
        ordered.append(current)

    return ordered

def run_bot():
    print("\n[OVERRIDE BOT ACTIVE] Focus your game window!")
    print(">>> Press [MIDDLE MOUSE CLICK] or 'q' at any time to STOP. <<<\n")
    time.sleep(2)

    with mss.mss() as sct:
        while True:
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            now = time.time()

            # 1. Screen capture
            screenshot = sct.grab(GAME_REGION)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 2. Run GPU detection
            results = model.predict(
                source=frame, device=0, conf=0.46, verbose=False
            )
            result = results[0]

            hazard_coords = []
            super_g_targets = []
            safe_pair_targets = []
            sequence_balloons = []
            standard_targets = []
            green_candidates = []

            # Step A: Collect all hazard coordinates first
            for box in result.boxes:
                if int(box.cls[0]) == HAZARD_CLASS_ID:
                    x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                    hazard_coords.append(
                        (
                            GAME_REGION["left"] + (x1 + x2) // 2,
                            GAME_REGION["top"] + (y1 + y2) // 2,
                        )
                    )

            # Step B: Parse all non-hazard targets and evaluate green balloons
            for box in result.boxes:
                class_id = int(box.cls[0])
                if class_id == HAZARD_CLASS_ID:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cx = GAME_REGION["left"] + (x1 + x2) // 2
                cy = GAME_REGION["top"] + (y1 + y2) // 2

                # Multiplier Guard: Always skip if too close to a hazard
                too_close_to_hazard = any(
                    math.hypot(cx - hx, cy - hy) < HAZARD_BUFFER_PX
                    for hx, hy in hazard_coords
                )
                if too_close_to_hazard:
                    continue

                # Categorize by model class
                if class_id == SUPER_G_CLASS_ID:
                    super_g_targets.append({"x": cx, "y": cy})
                elif class_id == SAFE_PAIR_CLASS_ID:
                    safe_pair_targets.append({"x": cx, "y": cy})
                elif class_id == SEQUENCE_CLASS_ID:
                    balloon_crop = frame[y1:y2, x1:x2]
                    color = detect_balloon_color(balloon_crop)
                    sequence_balloons.append(
                        {"x": cx, "y": cy, "color": color}
                    )
                else:
                    # Check if safe balloon is green
                    balloon_crop = frame[y1:y2, x1:x2]
                    color = detect_balloon_color(balloon_crop)
                    if color == "green":
                        green_candidates.append({"x": cx, "y": cy})
                    else:
                        standard_targets.append(
                            {
                                "x": cx,
                                "y": cy,
                                "is_priority": class_id == GEMINI_CLASS_ID,
                            }
                        )

            # Step C: Detect if End-Game Swarm Override is Active
            is_swarm_override = len(green_candidates) >= SWARM_OVERRIDE_THRESHOLD

            # 3. Action Execution
            executed_super_g = False

            # PRIORITY 1: Super G Event
            if super_g_targets:
                target = super_g_targets[0]
                completed = burst_click(
                    target["x"], target["y"], total_clicks=28, tap_gap=0.038
                )
                if not completed:
                    break
                recent_clicks.append((target["x"], target["y"], time.time() + 0.5))
                executed_super_g = True

            # PRIORITY 2: END-GAME SWARM OVERRIDE (Ignores Cooldown Completely!)
            elif is_swarm_override:
                # Sweep all green balloons across the screen immediately
                for target in sort_targets_by_flow(green_candidates):
                    if is_middle_click_pressed():
                        break
                    frenzy_tap(target["x"], target["y"])
                    time.sleep(SWARM_TAP_DELAY)  # 8ms rapid tap

            # PRIORITY 3: Sequence Round (When exactly 4 balloons are present)
            elif len(sequence_balloons) == 4:
                for target_color in SEQUENCE_ORDER:
                    if is_middle_click_pressed():
                        break
                    for balloon in sequence_balloons:
                        if balloon["color"] == target_color:
                            flow_click(balloon["x"], balloon["y"])
                            recent_clicks.append(
                                (
                                    balloon["x"],
                                    balloon["y"],
                                    time.time() + POPPED_COOLDOWN_SECONDS,
                                )
                            )
                            time.sleep(0.038)
                            break

            # PRIORITY 4: Safe Pairs
            elif len(safe_pair_targets) == 2:
                for target in safe_pair_targets:
                    if is_middle_click_pressed():
                        break
                    flow_click(target["x"], target["y"])
                    recent_clicks.append(
                        (
                            target["x"],
                            target["y"],
                            time.time() + POPPED_COOLDOWN_SECONDS,
                        )
                    )
                    time.sleep(0.02)

            # PRIORITY 5: Standard Round Play (Respects Cooldown)
            else:
                # Filter targets using cooldown ledger during normal play
                all_regular = standard_targets + [
                    {"x": g["x"], "y": g["y"], "is_priority": False}
                    for g in green_candidates
                ]
                available_targets = [
                    t for t in all_regular
                    if not is_spot_on_cooldown(t["x"], t["y"], now)
                ]

                if available_targets:
                    priority_balloons = [
                        t for t in available_targets if t["is_priority"]
                    ]
                    normal_balloons = [
                        t for t in available_targets if not t["is_priority"]
                    ]
                    smooth_path = priority_balloons + sort_targets_by_flow(
                        normal_balloons
                    )

                    for target in smooth_path:
                        if is_middle_click_pressed():
                            break
                        flow_click(target["x"], target["y"])
                        recent_clicks.append(
                            (
                                target["x"],
                                target["y"],
                                time.time() + POPPED_COOLDOWN_SECONDS,
                            )
                        )
                        time.sleep(0.022)

            # Emergency Stop Check after clicks
            if is_middle_click_pressed():
                print("\n[EMERGENCY STOP] Middle mouse button detected!")
                break

            # 4. Preview Window
            preview = result.plot()
            cv2.imshow("Tap Party Vision Bot", preview)

            # 5. Dynamic Loop Sleep
            if executed_super_g:
                time.sleep(0.05)
            elif is_swarm_override:
                time.sleep(SWARM_LOOP_DELAY)  # Fast 10ms frame loop during swarms
            else:
                time.sleep(NORMAL_LOOP_DELAY)  # Stable 40ms frame loop during normal play

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cv2.destroyAllWindows()
    print("[BOT STOPPED] Exited safely.")


if __name__ == "__main__":
    run_bot()