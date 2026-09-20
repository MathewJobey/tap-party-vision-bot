from ultralytics import YOLO

# Step 1: Load the trained custom model weights
model_path = r"runs/detect/train/weights/best.pt"
model = YOLO(model_path)

# Step 2: Point to the folder containing your 30 raw screenshots
folder_path = "dataset_raw"
# Step 3: Run detection across all images in the folder using the GPU
results = model.predict(
    source=folder_path,
    device=0,
    conf=0.2,
    save=True,
    project="test_outputs",
    name="raw_predictions",
    exist_ok=True,
)

# Step 4: Confirmation output
print("\nBatch prediction complete!")
print("Annotated images saved to: test_outputs/raw_predictions")