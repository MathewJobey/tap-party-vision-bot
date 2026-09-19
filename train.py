import torch
from ultralytics import YOLO

# Part 1: Hardware Setup
if torch.cuda.is_available():
    selected_device = 0
    gpu_name = torch.cuda.get_device_name(0)
    print(f"GPU detected: {gpu_name}. Training will run on GPU.")
else:
    selected_device = "cpu"
    print("No CUDA GPU detected. Training will run on CPU.")

# Part 2: Model Training Routine
if __name__ == "__main__":
    # Load the base YOLOv8 Small model
    model = YOLO("yolov8s.pt")

    # Start the training process
    model.train(
        data="data.yaml",
        epochs=50,
        imgsz=640,
        batch=16,
        device=selected_device,
        workers=2,
    )