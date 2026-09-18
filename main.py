import time
import cv2
import numpy as np
import pyautogui
import config
import vision

pyautogui.FAILSAFE = config.FAILSAFE
pyautogui.PAUSE = config.CLICK_PAUSE

print("Starting in 3 seconds... Bring your game window to the front!")
time.sleep(3)

start_time = time.time()
print("Bot active! Running for 60 seconds...")

while (time.time() - start_time) < config.MATCH_DURATION:
    # 1. Grab screen frame
    screenshot = pyautogui.screenshot(region=config.GAME_REGION)
    frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    # 2. Get positions of hazards and target candidates
    hazards = vision.find_hazard_centers(gray)
    candidates = vision.find_target_candidates(gray)

    # 3. Check candidates against known hazards
    for tx, ty in candidates:
        if (time.time() - start_time) >= config.MATCH_DURATION:
            break

        is_near_hazard = False
        for hx, hy in hazards:
            # Calculate distance between candidate balloon and hazard
            if np.hypot(tx - hx, ty - hy) < config.HAZARD_AVOID_RADIUS:
                is_near_hazard = True
                break

        # If it's not a hazard, click it!
        if not is_near_hazard:
            screen_x = config.GAME_REGION[0] + tx
            screen_y = config.GAME_REGION[1] + ty

            pyautogui.click(screen_x, screen_y)
            time.sleep(config.POST_CLICK_DELAY)
            break

print("60-second match complete! Stopped before the submission screen.")