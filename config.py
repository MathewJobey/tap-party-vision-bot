# Game window coordinates: (left, top, width, height)
GAME_REGION = (650, 100, 620, 915)

# Game timing
MATCH_DURATION = 60.0

# Hazard balloon template matching settings
HAZARD_TEMPLATE_PATH = "hazard.png"
HAZARD_SCALES = [0.55, 0.70, 0.85, 1.0, 1.15]
HAZARD_CONFIDENCE = 0.48

# Minimum pixel distance to keep away from a hazard center
HAZARD_AVOID_RADIUS = 45

# PyAutoGUI settings
FAILSAFE = True
CLICK_PAUSE = 0.01
POST_CLICK_DELAY = 0.02