import json
import base64
import tempfile
import os
import subprocess
import glob
from birdnet_analyzer.analyze import core
from flask import Flask, request, jsonify

app = Flask(__name__)

# 设置模型路径
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'model', 'BirdNET_GLOBAL_6K_V2.4_Model_FP32.tflite')
LABELS_PATH = os.path.join(os.path.dirname(__file__), 'model', 'BirdNET_GLOBAL_6K_V2.4_Labels.txt')

def convert_mp3_to_wav(mp3_path):
    """将 MP3 转换为 WAV 格式"""
    wav_path = mp3_path + '.wav'
    command = [
        'ffmpeg', '-y', '-i', mp3_path,
        '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1', wav_path
    ]
    try:
        subprocess.run(command, check=True, capture_output=True)
        print(f"Successfully converted {mp3_path} to {wav_path}")
        return wav_path
    except subprocess.CalledProcessError as e:
        print(f"Error converting MP3 to WAV: {e}")
        print(f"FFmpeg stderr: {e.stderr.decode()}")
        return None

def parse_table_file(table_path):
    """解析检测结果文件"""
    detections = []
    with open(table_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    if len(lines) < 2:
        return detections
    header = lines[0].strip().split('\t')
    for line in lines[1:]:
        cols = line.strip().split('\t')
        if len(cols) < 10:
            continue
        detection = {
            'species': cols[7],
            'species_code': cols[8],
            'confidence': float(cols[9]),
            'begin_time': float(cols[3]),
            'end_time': float(cols[4])
        }
        detections.append(detection)
    return detections

def predict(data):
    """SageMaker 预测函数"""
    input_path = None
    wav_path = None
    temp_dir = None
    try:
        # 解析输入
        if not data or 'audio' not in data:
            return {
                'statusCode': 400,
                'body': {
                    'message': 'Missing audio data in request',
                    'detections': []
                }
            }

        # 获取音频数据和格式
        audio_b64 = data['audio']
        audio_format = data.get('format', 'wav').lower()  # 默认为 wav
        audio_bytes = base64.b64decode(audio_b64)

        print(f"Processing {audio_format} audio file...")

        # 临时目录用于输出
        temp_dir = tempfile.mkdtemp()
        # 保存音频到临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{audio_format}', dir=temp_dir) as f:
            f.write(audio_bytes)
            input_path = f.name
        print(f"Saved audio to temporary file: {input_path}")

        # 如果是 MP3，转换为 WAV
        wav_path = input_path
        if audio_format == 'mp3':
            wav_path = convert_mp3_to_wav(input_path)
            if not wav_path:
                raise RuntimeError("MP3 to WAV conversion failed")

        print(f"Using model: {MODEL_PATH}")
        print(f"Using labels: {LABELS_PATH}")

        # 调用 BirdNET-Analyzer
        core.analyze(
            input=wav_path,
            output=temp_dir,
            min_conf=0.01,  # 更低阈值
            classifier=MODEL_PATH,
            rtype="table"
        )

        # 查找 .BirdNET.selection.table.txt 文件
        table_files = glob.glob(os.path.join(temp_dir, '*.BirdNET.selection.table.txt'))
        if not table_files:
            detections = []
        else:
            detections = parse_table_file(table_files[0])

        print(f"Formatted detections: {detections}")

        # 清理临时文件
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)
        if audio_format == 'mp3' and wav_path and os.path.exists(wav_path) and wav_path != input_path:
            os.unlink(wav_path)
        if temp_dir and os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try:
                    os.unlink(os.path.join(temp_dir, f))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass

        if not detections:
            return {
                'statusCode': 200,
                'body': {
                    'message': 'No bird species detected',
                    'detections': []
                }
            }
        else:
            return {
                'statusCode': 200,
                'body': {
                    'message': 'Success',
                    'detections': detections
                }
            }

    except Exception as e:
        # 确保清理临时文件
        if input_path and os.path.exists(input_path):
            os.unlink(input_path)
        if audio_format == 'mp3' and wav_path and os.path.exists(wav_path) and wav_path != input_path:
            os.unlink(wav_path)
        if temp_dir and os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try:
                    os.unlink(os.path.join(temp_dir, f))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass
                
        print(f"Error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': {
                'message': f'Error processing audio: {str(e)}',
                'detections': []
            }
        }

@app.route('/ping', methods=['GET'])
def ping():
    """健康检查端点"""
    return jsonify({'status': 'healthy'})

@app.route('/invocations', methods=['POST'])
def invoke():
    """推理端点"""
    if not request.is_json:
        return jsonify({
            'statusCode': 400,
            'body': {
                'message': 'Request must be JSON',
                'detections': []
            }
        }), 400

    data = request.get_json()
    result = predict(data)
    
    # 确保 body 是 JSON 对象而不是字符串
    if isinstance(result['body'], str):
        result['body'] = json.loads(result['body'])
    
    return jsonify(result), result['statusCode']

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080) 