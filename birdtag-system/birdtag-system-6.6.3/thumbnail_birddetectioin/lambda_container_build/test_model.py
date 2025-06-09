from ultralytics import YOLO
import cv2
import numpy as np
import json
from pathlib import Path

def test_model_output(image_path):
    """
    Test YOLO model inference and output detailed detection information.
    Analyzes image processing, model predictions, and coordinate normalization.
    
    Args:
        image_path (str): Path to the input image for testing
    """
    # Load YOLO model from current directory
    model = YOLO('./model.pt')
    
    # Read and validate input image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return
        
    # Get image dimensions
    height, width = img.shape[:2]
    print(f"\nImage size: {width}x{height}")
    
    # Execute model inference
    results = model(img)[0]
    
    # Log raw detection results
    print("\nRaw YOLO Results:")
    print(f"Number of detections: {len(results.boxes)}")
    
    # Process and display detailed detection information
    print("\nDetailed Detections:")
    for i, box in enumerate(results.boxes):
        # Extract class ID and confidence score
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        
        # Get class name from model
        class_name = model.names[cls_id]
        
        # Extract bounding box coordinates
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        
        # Calculate normalized coordinates
        norm_box = [
            float(x1 / width),
            float(y1 / height),
            float(x2 / width),
            float(y2 / height)
        ]
        
        print(f"\nDetection {i+1}:")
        print(f"  Class: {class_name}")
        print(f"  Confidence: {conf:.4f}")
        print(f"  Raw box: [{x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f}]")
        print(f"  Normalized box: {[f'{x:.4f}' for x in norm_box]}")
    
    # Display model class mapping
    print("\nModel Classes:")
    for cls_id, cls_name in model.names.items():
        print(f"  {cls_id}: {cls_name}")

if __name__ == "__main__":
    # Test model with multiple sample images
    test_images = [
        "./test_image.jpg",  # Test image in current directory
        "../test_images/crows_1.jpg",
        "../test_images/kingfisher_1.jpg",
        "../test_images/sparrow_1.jpg"
    ]
    
    for img_path in test_images:
        print(f"\n{'='*50}")
        print(f"Testing image: {img_path}")
        print(f"{'='*50}")
        test_model_output(img_path) 
