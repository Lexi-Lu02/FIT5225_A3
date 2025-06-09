import json
import os
from lambda_function import lambda_handler
from birdnet_analyzer.analyze import analyze

# 构造一个模拟的S3事件
MOCK_EVENT = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "upload/audio/test_audio.wav"}
            }
        }
    ]
}

class MockContext:
    function_name = "test_lambda"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test_lambda"
    aws_request_id = "test-request-id"

if __name__ == "__main__":
    analyze(
        input="test_audio.wav",
        output="./test_output",
        min_conf=0.1,
        sensitivity=1.0,
        overlap=0.0,
        threads=1,
        batch_size=1,
        lat=None,
        lon=None,
        week=None
    )
    # 你可以根据实际情况修改bucket/key，或放置一个本地测试音频文件
    # 运行lambda_handler
    response = lambda_handler(MOCK_EVENT, MockContext())
    print("Lambda Response:")
    print(json.dumps(json.loads(response["body"]), indent=2, ensure_ascii=False))
    # 检查输出格式
    required_keys = ["message", "media_id", "detected_species", "detection_segments", "file_location", "created_at"]
    body = json.loads(response["body"])
    missing = [k for k in required_keys if k not in body]
    if missing:
        print(f"❌ 缺少字段: {missing}")
    else:
        print("✅ 输出格式符合要求！") 