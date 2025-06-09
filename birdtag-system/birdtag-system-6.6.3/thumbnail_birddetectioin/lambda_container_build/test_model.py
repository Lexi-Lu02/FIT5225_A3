from ultralytics import YOLO
import cv2
import numpy as np
import json
from pathlib import Path

def test_model_output(image_path):
    """
    测试模型输出并打印详细信息
    """
    # 加载模型 - 修改为当前目录
    model = YOLO('./model.pt')
    
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image {image_path}")
        return
        
    # 获取图片尺寸
    height, width = img.shape[:2]
    print(f"\nImage size: {width}x{height}")
    
    # 运行推理
    results = model(img)[0]
    
    # 打印原始结果
    print("\nRaw YOLO Results:")
    print(f"Number of detections: {len(results.boxes)}")
    
    # 打印每个检测的详细信息
    print("\nDetailed Detections:")
    for i, box in enumerate(results.boxes):
        # 获取类别ID和置信度
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        
        # 获取类别名称
        class_name = model.names[cls_id]
        
        # 获取边界框坐标
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        
        # 计算归一化坐标
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
    
    # 打印模型类别信息
    print("\nModel Classes:")
    for cls_id, cls_name in model.names.items():
        print(f"  {cls_id}: {cls_name}")

if __name__ == "__main__":
    # 测试几张不同的图片 - 修改为当前目录下的测试图片
    test_images = [
        "./test_image.jpg",  # 使用当前目录的测试图片
        "../test_images/crows_1.jpg",
        "../test_images/kingfisher_1.jpg",
        "../test_images/sparrow_1.jpg"
    ]
    
    for img_path in test_images:
        print(f"\n{'='*50}")
        print(f"Testing image: {img_path}")
        print(f"{'='*50}")
        test_model_output(img_path) 