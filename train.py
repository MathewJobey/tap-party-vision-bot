import torch
from ultralytics import YOLO

# Detect whether NVIDIA GPU acceleration is available
if torch.cuda.is_available():
    selected_device = 0
    gpu_name = torch.cuda.get_device_name(0)
    print(f"GPU detected: {gpu_name}. Training will run on GPU.")
else:
    selected_device = "cpu"
    print("No CUDA GPU detected. Training will run on CPU.")

# Guard execution for Windows multi-processing
if __name__ == "__main__":
    # Load the base YOLOv8 Small architecture
    model = YOLO("yolov8s.pt")

    # Start the training cycle on the 258 images
    model.train(
        data="data.yaml",
        epochs=50,
        imgsz=640,
        batch=16,
        device=selected_device,
        workers=2,
    )