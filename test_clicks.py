import time
import pyautogui

# Built-in emergency brake: move your cursor to any corner of the screen to stop
pyautogui.FAILSAFE = True

print("Switch to the game now! You have 5 seconds to hover over a balloon...")
time.sleep(5)

print("Attempting 5 clicks...")
for click_count in range(5):
    pyautogui.click()
    time.sleep(0.05)

print("Finished test clicks.")