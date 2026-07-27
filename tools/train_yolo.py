import os
import sys
from pathlib import Path

def train_and_export_ui_model(dataset_yaml_path: str, epochs: int = 50, imgsz: int = 1024):
    """
    Train a custom YOLO model on a Web UI dataset (e.g. from Roboflow in YOLO/COCO format)
    and export the final model to ONNX format for fast local CPU inference in VisiFlow.
    """
    try:
        from ultralytics import YOLO
    except ImportError:
        print("Ultralytics is not installed. Please install it using: pip install ultralytics")
        sys.exit(1)

    print("=== Step 1: Initializing YOLO Nano Architecture ===")
    # Load a pretrained yolov8n configuration (or a custom yaml config if provided)
    # This initializes a lightweight ~5MB Nano model.
    model = YOLO("yolov8n.yaml")  # Loads the network configuration
    model = YOLO("yolov8n.pt")    # Transfers pretrained COCO weights for faster convergence

    print(f"\n=== Step 2: Training on Dataset: {dataset_yaml_path} ===")
    print(f"Parameters: Epochs={epochs}, Image Size={imgsz}")
    
    import torch
    device = 0 if torch.cuda.is_available() else "cpu"
    
    # Train the model. It's recommended to run this on a GPU (CUDA) enabled environment.
    # We use batch=4 to avoid CUDA Out of Memory (OOM) on consumer GPUs with 1024x1024 resolution.
    model.train(
        data=dataset_yaml_path,
        epochs=epochs,
        imgsz=imgsz,
        batch=4,
        device=device,
        workers=4,
        verbose=True
    )
    
    print("\n=== Step 3: Exporting Best Model to ONNX Format ===")
    # Exporting to ONNX enables ultra-fast inference on CPU without needing PyTorch.
    # The exported model will be saved in the runs/detect/train/weights directory.
    onnx_path = model.export(format="onnx", imgsz=imgsz)
    print(f"✅ Success! ONNX model exported to: {onnx_path}")
    
    # Copy best.onnx to the current directory as yolo26n.onnx for default VisiFlow usage
    try:
        import shutil
        dest = Path("yolo26n.onnx")
        shutil.copy(onnx_path, dest)
        print(f"✅ Copied model to: {dest.resolve()}")
    except Exception as e:
        print(f"Could not copy model file to root: {e}")

if __name__ == "__main__":
    # Example dataset structure (data.yaml) pointing to your train/val images:
    # names:
    #   0: button
    #   1: input
    #   2: dropdown
    #   3: icon
    
    # Check if data.yaml exists
    example_yaml = "data.yaml"
    if not os.path.exists(example_yaml):
        print(f"Please create a '{example_yaml}' file pointing to your labeled UI dataset before running.")
        print("You can easily download web UI datasets from Roboflow Universe (e.g. search 'Web UI element detection').")
        sys.exit(1)

    train_and_export_ui_model(example_yaml, epochs=50, imgsz=1024)
