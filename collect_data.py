import os
import time
import pyautogui

# Set up the exact coordinates for the game canvas
# Format: (left, top, width, height)
GAME_REGION = (650, 100, 620, 915)

# Folder where the cropped images will be saved
output_dir = "dataset_raw"
os.makedirs(output_dir, exist_ok=True)
# Give yourself time to click back into Chrome
print("You have 5 seconds to switch to the Tap Party tab...")
time.sleep(5)
print("Starting capture! Play normally for 30 seconds.")

total_screenshots = 30
for i in range(total_screenshots):
    # Capture ONLY the specified game boundary
    screenshot = pyautogui.screenshot(region=GAME_REGION)
    
    # Save the cropped frame
    file_path = os.path.join(output_dir, f"frame_{i:03d}.png")
    screenshot.save(file_path)
    
    print(f"Captured {i + 1}/{total_screenshots}: {file_path}")
    time.sleep(1.0)

print(f"\nDone! Saved {total_screenshots} cropped images to '{output_dir}'.")