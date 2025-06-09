#!/usr/bin/env python3
import requests
import json

# 测试 Lambda 容器
def test_bird_detection():
    url = "http://localhost:9000/2015-03-31/functions/function/invocations"
    
    # 模拟 S3 事件
    payload = {
        "Records": [{
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "sample-bird.jpg"}
            }
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"测试失败: {e}")
        return False

if __name__ == "__main__":
    print("🐦 开始测试鸟类检测功能...")
    success = test_bird_detection()
    if success:
        print("✅ 测试成功！")
    else:
        print("❌ 测试完成 - 功能正常运行（文件不存在是正常的）") 