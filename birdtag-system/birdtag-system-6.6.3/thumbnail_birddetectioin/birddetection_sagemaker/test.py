import base64
import json
import requests
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_local_endpoint():
    """测试本地运行的端点"""
    try:
        # 读取测试图片
        with open('test.jpg', 'rb') as f:
            img_b64 = base64.b64encode(f.read()).decode()

        # 构造请求数据
        data = {
            'image': img_b64
        }

        # 发送请求到本地端点
        response = requests.post(
            'http://localhost:8080/invocations',
            json=data
        )

        # 检查响应
        if response.status_code == 200:
            result = response.json()
            logger.info("Successfully got predictions:")
            logger.info(f"Labels: {result.get('labels', [])}")
            logger.info(f"Probabilities: {result.get('probs', [])}")
        else:
            logger.error(f"Error: {response.status_code}")
            logger.error(response.text)

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")

if __name__ == '__main__':
    test_local_endpoint()