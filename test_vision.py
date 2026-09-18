import time
import cv2
import numpy as np
import pyautogui

GAME_REGION = (650, 100, 620, 915)

# Load your cropped template
template_original = cv2.imread("hazard.png", cv2.IMREAD_GRAYSCALE)
if template_original is None:
    print("Error: 'hazard.png' not found in folder!")
    exit()

orig_h, orig_w = template_original.shape

# Define scale factors to catch both small and full-sized balloons
SCALES = [0.65, 0.80, 1.0, 1.20]
print("Starting in 3 seconds... Switch to your game window!")
time.sleep(3)

screenshot = pyautogui.screenshot(region=GAME_REGION)
frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
gray_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

all_boxes = []

# Scan across each defined size scale
for scale in SCALES:
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    resized_template = cv2.resize(template_original, (new_w, new_h))

    # Match template against the grayscale frame
    res = cv2.matchTemplate(gray_frame, resized_template, cv2.TM_CCOEFF_NORMED)
    
    # 65% similarity threshold
    locs = np.where(res >= 0.65)
    for pt in zip(*locs[::-1]):
        all_boxes.append([int(pt[0]), int(pt[1]), int(new_w), int(new_h)])
        # Clean up duplicate overlapping detections
clean_indices = cv2.dnn.NMSBoxes(
    all_boxes,
    [1.0] * len(all_boxes),
    score_threshold=0.5,
    nms_threshold=0.3
)

hazard_count = 0
if len(clean_indices) > 0:
    for idx in clean_indices.flatten():
        x, y, w, h = all_boxes[idx]
        # Draw red box around each detected danger balloon
        cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 0, 255), 3)
        hazard_count += 1

cv2.imwrite("hazard_check.png", frame_bgr)
print(f"Done! Detected {hazard_count} hazard balloon(s).")
print("Open 'hazard_check.png' to see the results.")