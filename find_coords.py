import time
import pyautogui

print("Move your mouse over the game window. Press Ctrl+C in this terminal to stop.")
print("Format: X, Y")

try:
    while True:
        # Get current mouse coordinates
        x, y = pyautogui.position()
        
        # Print position and overwrite the same terminal line
        position_str = f"X: {str(x).rjust(4)} | Y: {str(y).rjust(4)}"
        print(position_str, end="\r", flush=True)
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\nTracking stopped.")