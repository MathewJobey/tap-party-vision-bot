import cv2
import numpy as np
import config

# Preload the hazard template image in grayscale once at startup
hazard_template = cv2.imread(config.HAZARD_TEMPLATE_PATH, cv2.IMREAD_GRAYSCALE)

def find_hazard_centers(gray_frame):
    """Finds center coordinates (x, y) of all distraction balloons on screen."""
    if hazard_template is None:
        return []

    orig_h, orig_w = hazard_template.shape
    all_boxes = []

    for scale in config.HAZARD_SCALES:
        new_w = int(orig_w * scale)
        new_h = int(orig_h * scale)
        resized_tmpl = cv2.resize(hazard_template, (new_w, new_h))

        res = cv2.matchTemplate(gray_frame, resized_tmpl, cv2.TM_CCOEFF_NORMED)
        locs = np.where(res >= config.HAZARD_CONFIDENCE)

        for pt in zip(*locs[::-1]):
            all_boxes.append([int(pt[0]), int(pt[1]), int(new_w), int(new_h)])

    # Remove overlapping duplicate boxes
    indices = cv2.dnn.NMSBoxes(
        all_boxes, [1.0] * len(all_boxes), score_threshold=0.4, nms_threshold=0.3
    )

    centers = []
    if len(indices) > 0:
        for idx in indices.flatten():
            bx, by, bw, bh = all_boxes[idx]
            centers.append((bx + (bw // 2), by + (bh // 2)))

    return centers

def find_target_candidates(gray_frame):
    """Locates potential balloon targets using adaptive thresholding and erosion."""
    blurred = cv2.GaussianBlur(gray_frame, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 5
    )

    kernel = np.ones((3, 3), np.uint8)
    separated = cv2.erode(thresh, kernel, iterations=2)

    contours, _ = cv2.findContours(separated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    targets = []
    frame_h = gray_frame.shape[0]

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if 400 < area < 7500:
            x, y, w, h = cv2.boundingRect(cnt)

            # Skip header area (timer) and oversized shapes
            if y < 80 or w > 110 or h > 110:
                continue

            aspect_ratio = float(w) / h
            if 0.70 < aspect_ratio < 1.35:
                targets.append((x + (w // 2), y + (h // 2)))

    return targets