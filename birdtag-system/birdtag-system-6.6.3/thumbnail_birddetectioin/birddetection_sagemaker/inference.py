from flask import Flask, request, jsonify
import torch
from PIL import Image
import io
import base64
import numpy as np
from ultralytics import YOLO
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 确定模型路径
MODEL_PATH = os.getenv('MODEL_PATH', 'model.pt')  # 默认使用当前目录下的模型文件
logger.info(f"Loading model from: {MODEL_PATH}")

# 加载模型
try:
    model = YOLO(MODEL_PATH)
    logger.info("Model loaded successfully")
except Exception as e:
    logger.error(f"Error loading model: {str(e)}")
    raise

@app.route('/ping', methods=['GET'])
def ping():
    """健康检查端点"""
    return "pong", 200

@app.route('/invocations', methods=['POST'])
def predict():
    """处理推理请求"""
    try:
        # 验证输入
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400

        # 解码图片
        try:
            img_b64 = data['image']
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        except Exception as e:
            logger.error(f"Error decoding image: {str(e)}")
            return jsonify({"error": "Invalid image data"}), 400

        # 执行推理
        try:
            with torch.no_grad():
                results = model(img)
                result = results[0]  # 获取第一个结果
                
                # 提取检测结果
                boxes = result.boxes
                if len(boxes) == 0:
                    return jsonify({
                        "labels": [],
                        "probs": []
                    })

                # 获取类别和置信度
                labels = [model.names[int(cls)] for cls in boxes.cls]
                probs = boxes.conf.tolist()

                # 按置信度排序
                sorted_indices = np.argsort(probs)[::-1]
                labels = [labels[i] for i in sorted_indices]
                probs = [probs[i] for i in sorted_indices]

                return jsonify({
                    "labels": labels,
                    "probs": probs
                })

        except Exception as e:
            logger.error(f"Error during inference: {str(e)}")
            return jsonify({"error": "Error during model inference"}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)