import time
import cv2
import numpy as np
import pyautogui
import config
import vision

# Remove PyAutoGUI's built-in delay between commands
pyautogui.FAILSAFE = config.FAILSAFE
pyautogui.PAUSE = config.CLICK_PAUSE

print("Starting in 3 seconds... Switch to your game window!")
time.sleep(3)

start_time = time.time()
print("High-speed bot active! Popping balloons...")

while (time.time() - start_time) < config.MATCH_DURATION:
    # 1. Capture screen frame
    screenshot = pyautogui.screenshot(region=config.GAME_REGION)
    frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Find hazards and safe candidates
    hazards = vision.find_hazard_centers(gray)
    candidates = vision.find_target_candidates(gray)

    # 3. Click ALL safe candidates in the frame
    for tx, ty in candidates:
        # Check timer before every click
        if (time.time() - start_time) >= config.MATCH_DURATION:
            break

        # Check if this candidate is near a hazard
        is_near_hazard = False
        for hx, hy in hazards:
            if np.hypot(tx - hx, ty - hy) < config.HAZARD_AVOID_RADIUS:
                is_near_hazard = True
                break

        # If it's safe, click it immediately
        if not is_near_hazard:
            screen_x = config.GAME_REGION[0] + tx
            screen_y = config.GAME_REGION[1] + ty

            pyautogui.click(screen_x, screen_y)
            time.sleep(config.POST_CLICK_DELAY)

print("60 seconds complete! Bot stopped before the submit button.")