# Game window coordinates: (left, top, width, height)
GAME_REGION = (650, 100, 620, 915)

# Game duration in seconds
MATCH_DURATION = 60.0

# Hazard balloon template matching settings
HAZARD_TEMPLATE_PATH = "hazard.png"
# Trimmed from 5 to 3 sizes to speed up image scanning
HAZARD_SCALES = [0.60, 0.85, 1.10]
HAZARD_CONFIDENCE = 0.48

# Safe distance (in pixels) to keep away from any hazard balloon
HAZARD_AVOID_RADIUS = 50

# Input delays (set to 0 for maximum speed)
FAILSAFE = True
CLICK_PAUSE = 0.00
POST_CLICK_DELAY = 0.005