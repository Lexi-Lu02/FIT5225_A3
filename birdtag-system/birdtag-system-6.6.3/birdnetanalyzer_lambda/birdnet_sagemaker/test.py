import requests
import base64
import json
from datetime import datetime

def test_health():
    """测试健康检查端点"""
    response = requests.get('http://localhost:8080/ping')
    print("\nHealth Check:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

def test_inference():
    """测试推理端点"""
    # 读取测试音频文件
    with open('test_audio.wav', 'rb') as f:
        audio_bytes = f.read()
    
    # 转换为 base64
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    # 准备请求数据
    data = {
        'audio': audio_b64,
        'format': 'wav'
    }
    
    # 发送请求
    response = requests.post(
        'http://localhost:8080/invocations',
        json=data,
        headers={'Content-Type': 'application/json'}
    )
    
    print("\nInference Test:")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # 保存响应到 JSON 文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = f'test_result_{timestamp}.json'
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(response.json(), f, indent=2, ensure_ascii=False)
    
    print(f"\nResponse saved to: {result_file}")

if __name__ == '__main__':
    # 先测试健康检查
    test_health()
    
    # 再测试推理
    test_inference() 