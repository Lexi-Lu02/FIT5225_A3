#!/usr/bin/env python3
"""
简化的本地测试服务器
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import json
import hashlib
import uuid
import base64
import datetime
import os
import shutil

app = Flask(__name__)
CORS(app)

# 模拟用户数据库
users_db = {}

# 用户文件数据库
user_files_db = []

# 文件元数据和标签管理
file_metadata = {
    'http://localhost:8080/sample-images/sample1.jpg': {
        'tags': ['robin', 'garden', 'morning'],
        'upload_time': '2024-06-09T10:00:00Z',
        'bird_detected': True,
        'species': 'robin',
        'count': 2
    },
    'http://localhost:8080/sample-images/sample2.jpg': {
        'tags': ['sparrow', 'tree', 'afternoon'],
        'upload_time': '2024-06-09T11:00:00Z', 
        'bird_detected': True,
        'species': 'sparrow',
        'count': 1
    },
    'http://localhost:8080/sample-images/bird-photo.jpg': {
        'tags': ['eagle', 'mountain', 'wildlife'],
        'upload_time': '2024-06-09T12:00:00Z',
        'bird_detected': True,
        'species': 'eagle',
        'count': 1
    },
    'http://localhost:8080/sample-images/nature.mp4': {
        'tags': ['nature', 'forest'],
        'upload_time': '2024-06-09T13:00:00Z',
        'bird_detected': False
    }
}

# 通知订阅数据库
notification_subscriptions = {}

# 通知历史
notification_history = []

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# 静态文件服务
@app.route('/')
def index():
    return send_from_directory('.', 'BirdTag.html')

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

# 认证端点
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        # 检查用户是否已存在
        if email in users_db:
            return jsonify({'message': 'User already exists'}), 400
        
        # 注册新用户
        user_id = str(uuid.uuid4())
        users_db[email] = {
            'password': hash_password(password),
            'id': user_id
        }
        
        # 生成简单token (base64编码的用户信息)
        token_data = {
            'id': user_id,
            'email': email,
            'exp': int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
        }
        # 生成类似JWT格式的token (header.payload.signature)
        header = base64.b64encode(json.dumps({'typ': 'JWT', 'alg': 'none'}).encode()).decode()
        payload = base64.b64encode(json.dumps(token_data).encode()).decode()
        signature = base64.b64encode('fake-signature'.encode()).decode()
        token = f"{header}.{payload}.{signature}"
        
        return jsonify({
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'email': email,
                'id': user_id
            }
        })
        
    except Exception as e:
        return jsonify({'message': 'Registration failed', 'error': str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'message': 'Email and password required'}), 400
        
        # 验证用户
        if email not in users_db:
            return jsonify({'message': 'Invalid email or password'}), 401
        
        if users_db[email]['password'] != hash_password(password):
            return jsonify({'message': 'Invalid email or password'}), 401
        
        # 生成token
        token_data = {
            'id': users_db[email]['id'],
            'email': email,
            'exp': int((datetime.datetime.now() + datetime.timedelta(days=30)).timestamp())
        }
        # 生成类似JWT格式的token (header.payload.signature)
        header = base64.b64encode(json.dumps({'typ': 'JWT', 'alg': 'none'}).encode()).decode()
        payload = base64.b64encode(json.dumps(token_data).encode()).decode()
        signature = base64.b64encode('fake-signature'.encode()).decode()
        token = f"{header}.{payload}.{signature}"
        
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'email': email,
                'id': users_db[email]['id']
            }
        })
        
    except Exception as e:
        return jsonify({'message': 'Login failed', 'error': str(e)}), 500

# 简单的API端点
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'BirdTag本地测试服务器运行中',
        'users_count': len(users_db)
    })

@app.route('/api/bird-detection', methods=['POST'])
def bird_detection():
    """鸟类检测 - 代理到Docker容器"""
    import requests
    try:
        container_url = "http://localhost:9000/2015-03-31/functions/function/invocations"
        payload = {
            "Records": [{
                "s3": {
                    "bucket": {"name": request.json.get("bucket", "test-bucket")},
                    "object": {"key": request.json.get("key", "test.jpg")}
                }
            }]
        }
        
        response = requests.post(container_url, json=payload, timeout=30)
        return jsonify(response.json()), response.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 模拟其他API端点
@app.route('/api/<path:endpoint>', methods=['GET', 'POST', 'OPTIONS'])
def mock_api(endpoint):
    if request.method == 'OPTIONS':
        return '', 200
    
    return jsonify({
        'statusCode': 200,
        'message': f'模拟API端点: {endpoint}',
        'method': request.method,
        'data': request.get_json() if request.method == 'POST' else dict(request.args)
    })

# 文件上传端点
@app.route('/api/upload', methods=['POST'])
def upload_file():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # 创建上传目录
        upload_dir = 'uploaded_files'
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        
        # 保存文件到本地
        filename = file.filename
        safe_filename = filename.replace(' ', '_')  # 避免空格问题
        file_path = os.path.join(upload_dir, safe_filename)
        file.save(file_path)
        
        # 模拟文件上传成功
        file_id = str(uuid.uuid4())
        file_url = f'http://localhost:8080/uploaded_files/{safe_filename}'
        
        # 检查是否是图片文件
        is_image = filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))
        # 检查是否是音频文件
        is_audio = filename.lower().endswith(('.wav', '.mp3', '.flac', '.m4a'))
        # 检查是否是视频文件
        is_video = filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))
        
        # 模拟保存文件信息到数据库
        mock_file_data = {
            'id': file_id,
            'filename': safe_filename,
            'url': file_url,
            'size': os.path.getsize(file_path),
            'upload_time': datetime.datetime.now().isoformat(),
            'user_id': 'test-user',
            's3_url': file_url,
            'is_image': is_image,
            'is_audio': is_audio,
            'is_video': is_video,
            'local_path': file_path
        }
        
        # 添加到用户文件数据库
        user_files_db.append(file_url)
        
        # 为新上传的文件添加默认元数据
        file_metadata[file_url] = {
            'tags': ['uploaded'],
            'upload_time': datetime.datetime.now().isoformat(),
            'bird_detected': False,
            'detection_status': 'pending' if (is_image or is_audio or is_video) else 'skipped',
            'local_path': file_path,
            'filename': safe_filename
        }
        
        # 如果是图片文件，自动触发鸟类检测
        detection_result = None
        if is_image:
            try:
                detection_result = trigger_bird_detection(safe_filename)
                if detection_result:
                    print(f"🔍 处理检测结果: {detection_result}")
                    
                    # 解析检测结果 - 处理不同的返回格式
                    if detection_result.get('statusCode') == 200:
                        # 检查是否有body字段（Docker容器格式）
                        if 'body' in detection_result:
                            try:
                                body = json.loads(detection_result.get('body', '{}'))
                                detection_info = body.get('detection_results', {})
                            except json.JSONDecodeError:
                                # 如果body不是JSON，使用原始结果
                                detection_info = detection_result
                        else:
                            # 直接使用结果
                            detection_info = detection_result.get('detection_results', detection_result)
                        
                        print(f"📊 解析的检测信息: {detection_info}")
                        
                        # 更新文件元数据
                        species = detection_info.get('species')
                        confidence = detection_info.get('confidence', 0.0)
                        detected_objects = detection_info.get('detected_objects', 0)
                        bounding_boxes = detection_info.get('bounding_boxes', [])
                        
                        file_metadata[file_url].update({
                            'bird_detected': detected_objects > 0 or bool(species),
                            'detection_status': 'completed',
                            'detected_species': [species] if species else [],
                            'detection_boxes': bounding_boxes,
                            'confidence': confidence
                        })
                        
                        # 添加检测到的标签
                        if species and species not in file_metadata[file_url]['tags']:
                            file_metadata[file_url]['tags'].append(species)
                            
                        print(f"✅ 元数据已更新: {file_metadata[file_url]}")
                        
                        # 🔔 触发通知系统
                        if species and confidence > 0.5:  # 只有高置信度的检测才触发通知
                            try:
                                triggered_notifications = trigger_notifications(species, safe_filename, detection_info)
                                if triggered_notifications:
                                    print(f"📧 已发送 {len(triggered_notifications)} 条通知")
                                    file_metadata[file_url]['notifications_sent'] = len(triggered_notifications)
                            except Exception as e:
                                print(f"❌ 通知发送失败: {e}")
                                file_metadata[file_url]['notification_error'] = str(e)
                    else:
                        # 检测失败
                        file_metadata[file_url].update({
                            'detection_status': 'failed',
                            'detection_error': detection_result.get('body', 'Unknown error')
                        })
            except Exception as e:
                print(f"❌ 检测处理失败: {e}")
                file_metadata[file_url]['detection_status'] = 'failed'
                file_metadata[file_url]['detection_error'] = str(e)
        
        # 如果是音频文件，自动触发BirdNET音频分析
        elif is_audio:
            try:
                detection_result = trigger_audio_detection(safe_filename)
                if detection_result:
                    print(f"🎵 处理音频检测结果: {detection_result}")
                    
                    # 解析BirdNET检测结果
                    if detection_result.get('statusCode') == 200:
                        # 检查是否有body字段
                        if 'body' in detection_result:
                            try:
                                body = json.loads(detection_result.get('body', '{}'))
                                detection_info = body
                            except json.JSONDecodeError:
                                detection_info = detection_result
                        else:
                            detection_info = detection_result
                        
                        print(f"📊 音频检测信息: {detection_info}")
                        
                        # 更新文件元数据 - BirdNET格式
                        detected_species = detection_info.get('detected_species', [])
                        detection_segments = detection_info.get('detection_segments', [])
                        
                        # 计算最高置信度
                        max_confidence = 0.0
                        if detection_segments:
                            max_confidence = max(seg.get('confidence', 0.0) for seg in detection_segments)
                        
                        file_metadata[file_url].update({
                            'bird_detected': len(detected_species) > 0,
                            'detection_status': 'completed',
                            'detected_species': detected_species,
                            'detection_segments': detection_segments,
                            'confidence': max_confidence
                        })
                        
                        # 添加检测到的标签
                        for species in detected_species:
                            if species and species not in file_metadata[file_url]['tags']:
                                file_metadata[file_url]['tags'].append(species)
                        
                        print(f"✅ 音频元数据已更新: {file_metadata[file_url]}")
                        
                        # 🔔 触发通知系统
                        if detected_species and max_confidence > 0.3:  # 音频检测置信度阈值较低
                            try:
                                # 为每个检测到的物种发送通知
                                for species in detected_species:
                                    triggered_notifications = trigger_notifications(species, safe_filename, detection_info)
                                    if triggered_notifications:
                                        print(f"📧 已为物种 {species} 发送 {len(triggered_notifications)} 条通知")
                            except Exception as e:
                                print(f"❌ 音频通知发送失败: {e}")
                                file_metadata[file_url]['notification_error'] = str(e)
                    else:
                        # 检测失败
                        file_metadata[file_url].update({
                            'detection_status': 'failed',
                            'detection_error': detection_result.get('body', 'Unknown error')
                        })
            except Exception as e:
                print(f"❌ 音频检测处理失败: {e}")
                file_metadata[file_url]['detection_status'] = 'failed'
                file_metadata[file_url]['detection_error'] = str(e)
        
        # 如果是视频文件，自动触发视频检测
        elif is_video:
            try:
                detection_result = trigger_video_detection(safe_filename)
                if detection_result:
                    print(f"🎞 处理视频检测结果: {detection_result}")
                    
                    # 解析视频检测结果
                    if detection_result.get('statusCode') == 200:
                        detection_info = detection_result.get('detection_results', {})
                        print(f"📊 视频检测信息: {detection_info}")
                        
                        # 更新文件元数据 - 视频检测格式
                        detected_objects = detection_info.get('detected_objects', 0)
                        bounding_boxes = detection_info.get('bounding_boxes', [])
                        detected_species = detection_info.get('detected_species', [])
                        
                        file_metadata[file_url].update({
                            'bird_detected': detected_objects > 0 and len(detected_species) > 0,
                            'detection_status': 'completed',
                            'detected_objects': detected_objects,
                            'detection_boxes': bounding_boxes,
                            'detected_species': detected_species,
                            'total_frames': detection_info.get('total_frames', 0),
                            'video_duration': detection_info.get('video_duration', 0),
                            'confidence': detection_info.get('confidence', 0.0)
                        })
                        
                        # 添加检测到的标签
                        if detected_objects > 0 and len(detected_species) > 0:
                            if 'video' not in file_metadata[file_url]['tags']:
                                file_metadata[file_url]['tags'].append('video')
                        
                        # 添加检测到的物种标签
                        for species in detected_species:
                            if species and species not in file_metadata[file_url]['tags']:
                                file_metadata[file_url]['tags'].append(species)
                        
                        print(f"✅ 视频元数据已更新: {file_metadata[file_url]}")
                        
                        # 🔔 触发通知系统
                        if detected_species:
                            try:
                                for species in detected_species:
                                    triggered_notifications = trigger_notifications(species, safe_filename, detection_info)
                                    if triggered_notifications:
                                        print(f"📧 已为视频物种 {species} 发送 {len(triggered_notifications)} 条通知")
                            except Exception as e:
                                print(f"❌ 视频通知发送失败: {e}")
                                file_metadata[file_url]['notification_error'] = str(e)
                    else:
                        # 检测失败
                        file_metadata[file_url].update({
                            'detection_status': 'failed',
                            'detection_error': detection_result.get('body', 'Unknown error')
                        })
            except Exception as e:
                print(f"❌ 视频检测处理失败: {e}")
                file_metadata[file_url]['detection_status'] = 'failed'
                file_metadata[file_url]['detection_error'] = str(e)
        
        response_data = {
            'statusCode': 200,
            'message': 'File uploaded successfully',
            'file': mock_file_data
        }
        
        if detection_result:
            response_data['detection_result'] = detection_result
            
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 提供上传的文件
@app.route('/uploaded_files/<filename>')
def serve_uploaded_file(filename):
    try:
        file_path = os.path.join('uploaded_files', filename)
        
        if os.path.exists(file_path):
            return send_file(file_path)
        else:
            return "File not found", 404
    except Exception as e:
        return f"Error serving file: {str(e)}", 500

def trigger_bird_detection(filename):
    """触发鸟类检测"""
    try:
        import requests
        import base64
        import os
        
        # 读取真实的图片文件
        file_path = os.path.join('uploaded_files', filename)
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'File not found: {file_path}',
                    'message': 'Real file is required for detection'
                })
            }
        
        # 将图片文件编码为base64
        with open(file_path, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        # 调用鸟类检测容器，传递真实图片数据
        container_url = "http://localhost:9000/2015-03-31/functions/function/invocations"
        payload = {
            "image_data": image_data,
            "filename": filename,
            "bucket": "local-test-bucket",
            "key": filename
        }
        
        print(f"🐦 开始检测图片: {filename}")
        response = requests.post(container_url, json=payload, timeout=30)
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ 检测完成: {result}")
                return result
            except Exception as e:
                print(f"❌ 解析检测结果失败: {e}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': f'Failed to parse detection result: {str(e)}',
                        'message': 'Real detection failed'
                    })
                }
        else:
            print(f"❌ 检测失败: {response.status_code}")
            return {
                'statusCode': response.status_code,
                'body': json.dumps({
                    'error': f'Detection service error: {response.status_code}',
                    'message': 'Real detection service failed'
                })
            }
            
    except Exception as e:
        print(f"❌ 检测异常: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Detection exception: {str(e)}',
                'message': 'Real detection failed with exception'
            })
        }

def trigger_audio_detection(filename):
    """触发BirdNET音频分析"""
    try:
        import requests
        import shutil
        import os
        
        # 读取真实的音频文件
        file_path = os.path.join('uploaded_files', filename)
        if not os.path.exists(file_path):
            print(f"❌ 音频文件不存在: {file_path}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'Audio file not found: {file_path}',
                    'message': 'Real audio file is required for analysis'
                })
            }
        
        # 为本地测试，将音频文件复制到当前目录供容器访问
        # BirdNET容器期望文件在工作目录中
        local_audio_file = filename
        shutil.copy2(file_path, local_audio_file)
        print(f"📋 已复制音频文件: {file_path} -> {local_audio_file}")
        
        # 调用BirdNET分析容器
        container_url = "http://localhost:9001/2015-03-31/functions/function/invocations"
        
        # 构建符合BirdNET Lambda期望的S3事件格式
        payload = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "local-test-bucket"},
                    "object": {"key": local_audio_file}
                }
            }]
        }
        
        print(f"🎵 开始BirdNET音频分析: {filename}")
        response = requests.post(container_url, json=payload, timeout=120)  # 音频分析需要更长时间
        
        # 清理临时文件
        try:
            if os.path.exists(local_audio_file):
                os.remove(local_audio_file)
                print(f"🧹 已清理临时文件: {local_audio_file}")
        except Exception as e:
            print(f"⚠️ 清理临时文件失败: {e}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"✅ 音频分析完成: {result}")
                return result
            except Exception as e:
                print(f"❌ 解析音频分析结果失败: {e}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({
                        'error': f'Failed to parse audio analysis result: {str(e)}',
                        'message': 'Real audio analysis failed'
                    })
                }
        else:
            print(f"❌ 音频分析失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return {
                'statusCode': response.status_code,
                'body': json.dumps({
                    'error': f'BirdNET service error: {response.status_code}',
                    'message': 'Real audio analysis service failed',
                    'response': response.text
                })
            }
            
    except Exception as e:
        print(f"❌ 音频分析异常: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Audio analysis exception: {str(e)}',
                'message': 'Real audio analysis failed with exception'
            })
        }

def trigger_video_detection(filename):
    """触发视频检测 - 提取关键帧并使用YOLO分析"""
    try:
        import requests
        import base64
        import os
        import tempfile
        
        # 读取真实的视频文件
        file_path = os.path.join('uploaded_files', filename)
        if not os.path.exists(file_path):
            print(f"❌ 视频文件不存在: {file_path}")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'error': f'Video file not found: {file_path}',
                    'message': 'Real video file is required for analysis'
                })
            }
        
        # 使用FFmpeg提取视频帧（每5秒提取一帧）
        frames_extracted = extract_video_frames(file_path, filename)
        if not frames_extracted:
            print(f"❌ 无法提取视频帧: {filename}")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': 'Failed to extract video frames',
                    'message': 'Video frame extraction failed'
                })
            }
        
        print(f"📷 已提取 {len(frames_extracted)} 帧: {filename}")
        
        # 对每一帧进行YOLO检测
        total_detections = 0
        all_bounding_boxes = []
        max_confidence = 0.0
        detected_species = set()
        
        for i, frame_path in enumerate(frames_extracted):
            try:
                # 将帧文件编码为base64
                with open(frame_path, 'rb') as f:
                    frame_data = base64.b64encode(f.read()).decode('utf-8')
                
                # 调用YOLO检测容器
                container_url = "http://localhost:9000/2015-03-31/functions/function/invocations"
                payload = {
                    "image_data": frame_data,
                    "filename": f"frame_{i}_{filename}",
                    "bucket": "local-test-bucket",
                    "key": f"frame_{i}_{filename}"
                }
                
                print(f"🔍 检测第 {i+1} 帧...")
                response = requests.post(container_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'body' in result:
                        body = json.loads(result['body'])
                        detection_info = body.get('detection_results', {})
                        
                        detected_objects = detection_info.get('detected_objects', 0)
                        if detected_objects > 0:
                            total_detections += detected_objects
                            confidence = detection_info.get('confidence', 0.0)
                            max_confidence = max(max_confidence, confidence)
                            
                            # 添加边界框信息（包含帧信息）
                            boxes = detection_info.get('bounding_boxes', [])
                            for box in boxes:
                                # 确保box是list格式，添加帧信息
                                if isinstance(box, list) and len(box) >= 4:
                                    box_info = {
                                        'x': box[0],
                                        'y': box[1], 
                                        'width': box[2] - box[0],
                                        'height': box[3] - box[1],
                                        'frame': i,
                                        'timestamp': i * 5
                                    }
                                    all_bounding_boxes.append(box_info)
                            
                            # 添加检测到的物种
                            species = detection_info.get('species')
                            if species:
                                detected_species.add(species)
                
                # 清理临时帧文件
                try:
                    os.remove(frame_path)
                except:
                    pass
                    
            except Exception as e:
                print(f"❌ 第 {i+1} 帧检测失败: {e}")
                continue
        
        # 构建视频检测结果
        video_detection_result = {
            'statusCode': 200,
            'detection_results': {
                'detected_objects': total_detections,
                'total_frames': len(frames_extracted),
                'confidence': max_confidence,
                'bounding_boxes': all_bounding_boxes,
                'detected_species': list(detected_species),
                'video_duration': len(frames_extracted) * 5  # 估算视频时长
            }
        }
        
        print(f"✅ 视频检测完成: 总计 {total_detections} 个检测，{len(detected_species)} 个物种")
        return video_detection_result
             
    except Exception as e:
        print(f"❌ 视频检测异常: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Video detection exception: {str(e)}',
                'message': 'Real video detection failed with exception'
            })
        }

def extract_video_frames(video_path, filename):
    """提取视频帧"""
    try:
        import subprocess
        import tempfile
        import os
        
        # 创建临时目录存储帧
        temp_dir = tempfile.mkdtemp()
        base_name = os.path.splitext(filename)[0]
        
        # 使用FFmpeg每5秒提取一帧
        cmd = [
            'ffmpeg', '-i', video_path,
            '-vf', 'fps=1/5',  # 每5秒一帧
            '-q:v', '2',  # 高质量
            f'{temp_dir}/{base_name}_frame_%03d.jpg'
        ]
        
        print(f"🎬 提取视频帧: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ FFmpeg错误: {result.stderr}")
            return []
        
        # 收集提取的帧文件
        frame_files = []
        for f in os.listdir(temp_dir):
            if f.endswith('.jpg'):
                frame_files.append(os.path.join(temp_dir, f))
        
        frame_files.sort()  # 确保按顺序排列
        return frame_files
        
    except Exception as e:
        print(f"❌ 视频帧提取失败: {e}")
        return []

# 媒体文件列表端点
@app.route('/api/media', methods=['GET'])
def get_media():
    # 返回真实上传的文件，包含检测到的物种信息
    real_files = []
    
    # 从user_files_db获取真实文件
    for file_url in user_files_db:
        filename = file_url.split('/')[-1]
        metadata = file_metadata.get(file_url, {})
        
        # 获取检测到的物种信息
        detected_species = metadata.get('detected_species', [])
        tags = metadata.get('tags', [])
        
        # 组合用户标签和检测到的物种（用英文）
        all_tags = []
        if detected_species:
            all_tags.extend(detected_species)  # 已经是英文的物种名
        
        # 添加用户自定义标签（排除已经存在的物种名）
        for tag in tags:
            if tag not in ['uploaded'] and tag not in detected_species:
                all_tags.append(tag)
        
        real_files.append({
            'id': filename,
            'filename': filename,
            'thumbnail': file_url,
            'upload_time': metadata.get('upload_time', datetime.datetime.now().isoformat()),
            'tags': all_tags,
            'bird_detected': metadata.get('bird_detected', False),
            'detection_status': metadata.get('detection_status', 'pending'),
            'detected_species': detected_species,
            'confidence': metadata.get('confidence', 0),
            'url': file_url
        })
    
    return jsonify({
        'statusCode': 200,
        'files': real_files,
        'total': len(real_files)
    })

# 搜索端点
@app.route('/api/v1/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        print(f"🔍 收到搜索请求: {data}")
        
        # 检查是否是标签计数搜索（对象形式如 {"sparrow": 1}）
        if data and isinstance(data, dict) and any(isinstance(v, int) for v in data.values()):
            # 标签计数搜索
            search_tags = data
            print(f"📋 标签计数搜索: {search_tags}")
            
            search_results = []
            
            for file_url in user_files_db:
                filename = file_url.split('/')[-1]
                metadata = file_metadata.get(file_url, {})
                
                # 检查文件是否满足任一标签要求（OR操作）
                matches_any_tag = False
                
                for tag_species, required_count in search_tags.items():
                    # 检查检测到的物种
                    detected_species = metadata.get('detected_species', [])
                    # 检查用户添加的标签
                    user_tags = metadata.get('tags', [])
                    
                    # 计算该物种在此文件中的出现次数（大小写不敏感）
                    species_count = 0
                    
                    # 从检测到的物种中计数（大小写不敏感）
                    for species in detected_species:
                        if species.lower() == tag_species.lower():
                            species_count += 1
                    
                    # 从用户标签中计数（大小写不敏感）
                    for tag in user_tags:
                        if tag.lower() == tag_species.lower():
                            species_count += 1
                    
                    # 如果该物种达到要求的最小数量，则包含此文件
                    if species_count >= required_count:
                        matches_any_tag = True
                        break  # 找到一个匹配就足够了
                
                if matches_any_tag:
                    # 构建媒体对象
                    detected_species = metadata.get('detected_species', [])
                    tags = metadata.get('tags', [])
                    
                    # 组合用户标签和检测到的物种
                    all_tags = []
                    if detected_species:
                        all_tags.extend(detected_species)
                    
                    # 添加用户自定义标签（排除已经存在的物种名）
                    for tag in tags:
                        if tag not in ['uploaded'] and tag not in detected_species:
                            all_tags.append(tag)
                    
                    # 判断文件类型
                    file_type = 'image'
                    if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        file_type = 'video'
                    elif filename.lower().endswith(('.wav', '.mp3', '.flac', '.m4a')):
                        file_type = 'audio'
                    
                    media_obj = {
                        'id': filename,
                        'original_name': filename,
                        'filename': filename,
                        's3_path': file_url,
                        'thumbnail': file_url,
                        'created_at': metadata.get('upload_time', datetime.datetime.now().isoformat()),
                        'upload_time': metadata.get('upload_time', datetime.datetime.now().isoformat()),
                        'file_type': file_type,
                        'tags': all_tags,
                        'bird_detected': metadata.get('bird_detected', False),
                        'detection_status': metadata.get('detection_status', 'pending'),
                        'detected_species': detected_species,
                        'detection_boxes': metadata.get('detection_boxes', []),
                        'detection_segments': metadata.get('detection_segments', []),
                        'confidence': metadata.get('confidence', 0),
                        'url': file_url
                    }
                    
                    search_results.append(media_obj)
            
            print(f"✅ 标签搜索找到 {len(search_results)} 个匹配文件")
            
        else:
            # 文本搜索（原有逻辑）
            query = data.get('query', '') if data else ''
            print(f"📝 文本搜索: '{query}'")
            
            search_results = []
            
            for file_url in user_files_db:
                filename = file_url.split('/')[-1]
                metadata = file_metadata.get(file_url, {})
                
                # 检查是否匹配搜索条件
                should_include = False
                if not query:
                    # 如果没有搜索词，包含所有文件
                    should_include = True
                else:
                    # 在文件名中搜索
                    if query.lower() in filename.lower():
                        should_include = True
                    # 在检测到的物种中搜索
                    detected_species = metadata.get('detected_species', [])
                    for species in detected_species:
                        if query.lower() in species.lower():
                            should_include = True
                            break
                    # 在标签中搜索
                    tags = metadata.get('tags', [])
                    for tag in tags:
                        if query.lower() in tag.lower():
                            should_include = True
                            break
                
                if should_include:
                    # 获取检测到的物种信息
                    detected_species = metadata.get('detected_species', [])
                    tags = metadata.get('tags', [])
                    
                    # 组合用户标签和检测到的物种
                    all_tags = []
                    if detected_species:
                        all_tags.extend(detected_species)
                    
                    # 添加用户自定义标签（排除已经存在的物种名）
                    for tag in tags:
                        if tag not in ['uploaded'] and tag not in detected_species:
                            all_tags.append(tag)
                    
                    # 判断文件类型
                    file_type = 'image'
                    if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
                        file_type = 'video'
                    elif filename.lower().endswith(('.wav', '.mp3', '.flac', '.m4a')):
                        file_type = 'audio'
                    
                    # 构建媒体对象
                    media_obj = {
                        'id': filename,
                        'original_name': filename,
                        'filename': filename,
                        's3_path': file_url,
                        'thumbnail': file_url,
                        'created_at': metadata.get('upload_time', datetime.datetime.now().isoformat()),
                        'upload_time': metadata.get('upload_time', datetime.datetime.now().isoformat()),
                        'file_type': file_type,
                        'tags': all_tags,
                        'bird_detected': metadata.get('bird_detected', False),
                        'detection_status': metadata.get('detection_status', 'pending'),
                        'detected_species': detected_species,
                        'detection_boxes': metadata.get('detection_boxes', []),
                        'detection_segments': metadata.get('detection_segments', []),
                        'confidence': metadata.get('confidence', 0),
                        'url': file_url
                    }
                    
                    search_results.append(media_obj)
        
        return jsonify({
            'statusCode': 200,
            'results': search_results,
            'total': len(search_results),
            'query': data
        })
        
    except Exception as e:
        print(f"❌ 搜索错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 获取文件元数据
@app.route('/api/file/<path:file_url>', methods=['GET'])
def get_file_metadata(file_url):
    try:
        # 构建完整URL
        full_url = f"http://localhost:8080/sample-images/{file_url}"
        metadata = file_metadata.get(full_url, {
            'tags': [],
            'upload_time': datetime.datetime.now().isoformat(),
            'bird_detected': False,
            'detection_status': 'not_started'
        })
        
        return jsonify({
            'statusCode': 200,
            'metadata': metadata,
            'url': full_url
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 检测状态端点
@app.route('/api/detection-status/<path:file_url>', methods=['GET'])
def get_detection_status(file_url):
    try:
        full_url = f"http://localhost:8080/sample-images/{file_url}"
        metadata = file_metadata.get(full_url, {})
        
        status_info = {
            'detection_status': metadata.get('detection_status', 'not_started'),
            'bird_detected': metadata.get('bird_detected', False),
            'detected_species': metadata.get('detected_species', []),
            'detection_boxes': metadata.get('detection_boxes', []),
            'detection_error': metadata.get('detection_error')
        }
        
        return jsonify({
            'statusCode': 200,
            'status': status_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 标签操作端点
@app.route('/api/tags/add', methods=['POST'])
def add_tags():
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        species = data.get('species')
        count = data.get('count', 1)
        
        if not file_url or not species:
            return jsonify({'error': 'file_url and species required'}), 400
        
        # 更新文件元数据
        if file_url not in file_metadata:
            file_metadata[file_url] = {'tags': [], 'bird_detected': False}
        
        if species not in file_metadata[file_url]['tags']:
            file_metadata[file_url]['tags'].append(species)
        
        file_metadata[file_url]['bird_detected'] = True
        file_metadata[file_url]['species'] = species
        file_metadata[file_url]['count'] = count
        
        return jsonify({
            'statusCode': 200,
            'message': 'Tags added successfully',
            'metadata': file_metadata[file_url]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags/remove', methods=['POST'])
def remove_tags():
    try:
        data = request.get_json()
        file_url = data.get('file_url')
        species = data.get('species')
        
        if not file_url or not species:
            return jsonify({'error': 'file_url and species required'}), 400
        
        # 更新文件元数据
        if file_url in file_metadata and species in file_metadata[file_url]['tags']:
            file_metadata[file_url]['tags'].remove(species)
            
            # 如果没有更多鸟类标签，设置bird_detected为False
            bird_tags = ['robin', 'sparrow', 'eagle', 'owl', 'hawk', 'cardinal']
            has_bird_tags = any(tag in file_metadata[file_url]['tags'] for tag in bird_tags)
            if not has_bird_tags:
                file_metadata[file_url]['bird_detected'] = False
        
        return jsonify({
            'statusCode': 200,
            'message': 'Tags removed successfully',
            'metadata': file_metadata.get(file_url, {})
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 提供示例图片文件
@app.route('/sample-images/<filename>')
def serve_sample_image(filename):
    try:
        # 首先检查是否有用户上传的真实文件
        uploaded_file_path = os.path.join('uploaded_files', filename)
        if os.path.exists(uploaded_file_path):
            # 如果存在真实上传的文件，直接返回
            return send_file(uploaded_file_path)
        
        # 如果没有真实文件，生成示例图片（仅用于演示文件）
        import io
        from PIL import Image
        
        # 创建一个简单的彩色图片
        img = Image.new('RGB', (600, 400))
        pixels = img.load()
        
        # 根据文件名创建不同颜色的图片
        if 'sample1' in filename:
            color = (100, 150, 200)  # 蓝色
        elif 'sample2' in filename:
            color = (150, 200, 100)  # 绿色  
        elif 'bird-photo' in filename:
            color = (200, 150, 100)  # 橙色
        else:
            color = (150, 150, 150)  # 灰色
            
        for i in range(600):
            for j in range(400):
                pixels[i, j] = color
        
        # 添加一些文字
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        
        # 尝试使用默认字体
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # 获取这个文件的检测结果
        full_url = f"http://localhost:8080/sample-images/{filename}"
        metadata = file_metadata.get(full_url, {})
        
        # 显示图片信息和检测结果
        y_pos = 50
        draw.text((50, y_pos), f"示例图片: {filename}", fill=(255, 255, 255), font=font)
        y_pos += 30
        draw.text((50, y_pos), "这是演示图片", fill=(200, 200, 200), font=font)
        
        # 转换为字节流
        img_io = io.BytesIO()
        img.save(img_io, 'JPEG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/jpeg')
        
    except Exception as e:
        # 如果PIL不可用，返回简单的文本响应
        return f"Sample image: {filename}", 200, {'Content-Type': 'text/plain'}

# 新增：显示检测结果详情的API
@app.route('/api/detection-result/<path:filename>', methods=['GET'])
def get_detection_result(filename):
    try:
        # 尝试多种URL格式查找文件元数据
        possible_urls = [
            f"http://localhost:8080/sample-images/{filename}",
            f"http://localhost:8080/uploaded_files/{filename}",
            filename
        ]
        
        metadata = {}
        full_url = None
        
        for url in possible_urls:
            if url in file_metadata:
                metadata = file_metadata[url]
                full_url = url
                break
        
        # 如果没找到元数据，查找是否有上传的文件
        uploaded_file_path = os.path.join('uploaded_files', filename)
        if os.path.exists(uploaded_file_path) and not metadata:
            # 为上传但未检测的文件创建基本元数据
            full_url = f"http://localhost:8080/uploaded_files/{filename}"
            metadata = {
                'detection_status': 'not_started',
                'bird_detected': False,
                'detected_species': [],
                'detection_boxes': [],
                'confidence': None,
                'upload_time': datetime.datetime.fromtimestamp(os.path.getmtime(uploaded_file_path)).isoformat(),
                'tags': ['uploaded']
            }
        
        detection_info = {
            'filename': filename,
            'image_url': full_url or f"http://localhost:8080/sample-images/{filename}",
            'detection_status': metadata.get('detection_status', 'not_started'),
            'bird_detected': metadata.get('bird_detected', False),
            'detected_species': metadata.get('detected_species', []),
            'detection_boxes': metadata.get('detection_boxes', []),
            'confidence': metadata.get('confidence', None),
            'upload_time': metadata.get('upload_time', None),
            'tags': metadata.get('tags', []),
            'file_exists': os.path.exists(uploaded_file_path) if uploaded_file_path else True
        }
        
        return jsonify({
            'statusCode': 200,
            'result': detection_info
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 新增：获取文件标签的API
@app.route('/api/tags/<path:filename>', methods=['GET'])
def get_file_tags(filename):
    try:
        # 尝试多种URL格式查找文件元数据
        possible_urls = [
            f"http://localhost:8080/sample-images/{filename}",
            f"http://localhost:8080/uploaded_files/{filename}",
            filename
        ]
        
        metadata = {}
        for url in possible_urls:
            if url in file_metadata:
                metadata = file_metadata[url]
                break
        
        # 如果没找到元数据，查找是否有上传的文件
        uploaded_file_path = os.path.join('uploaded_files', filename)
        if os.path.exists(uploaded_file_path) and not metadata:
            # 为上传但未标记的文件创建基本元数据
            metadata = {
                'tags': ['uploaded'],
                'bird_detected': metadata.get('bird_detected', False),
                'detected_species': metadata.get('detected_species', [])
            }
        
        return jsonify({
            'statusCode': 200,
            'tags': metadata.get('tags', []),
            'detected_species': metadata.get('detected_species', []),
            'bird_detected': metadata.get('bird_detected', False)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 新增：获取所有可用物种列表的API
@app.route('/api/species', methods=['GET'])
def get_species_list():
    try:
        # 返回鸟类物种列表
        species_list = [
            'Blue Jay', 'Robin', 'Cardinal', 'Sparrow', 'Eagle', 'Hawk', 
            'Owl', 'Pigeon', 'Crow', 'Woodpecker', 'Hummingbird', 'Finch',
            'Warbler', 'Thrush', 'Oriole', 'Blackbird', 'Chickadee', 'Nuthatch'
        ]
        
        return jsonify({
            'statusCode': 200,
            'species': species_list
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 调试端点：查看所有文件元数据
@app.route('/api/debug/metadata', methods=['GET'])
def debug_metadata():
    try:
        return jsonify({
            'statusCode': 200,
            'file_metadata': file_metadata,
            'total_files': len(file_metadata)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 删除文件端点
@app.route('/api/v1/files/delete', methods=['POST'])
def delete_files():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 获取要删除的文件列表
        file_keys = data.get('fileKeys', [])
        if not file_keys:
            return jsonify({'error': 'No fileKeys provided'}), 400
        
        deleted_files = []
        errors = []
        
        for file_key in file_keys:
            try:
                # 对于本地测试，file_key就是完整的URL
                file_url = file_key
                
                # 如果file_key不包含协议，构建完整URL
                if not file_key.startswith('http'):
                    if file_key.startswith('uploaded_files/'):
                        file_url = f'http://localhost:8080/{file_key}'
                    else:
                        file_url = f'http://localhost:8080/sample-images/{file_key}'
                
                # 从文件元数据中删除
                if file_url in file_metadata:
                    metadata = file_metadata[file_url]
                    
                    # 如果是用户上传的文件，删除本地文件
                    if 'local_path' in metadata:
                        local_path = metadata['local_path']
                        if os.path.exists(local_path):
                            os.remove(local_path)
                            print(f"🗑️ 已删除本地文件: {local_path}")
                    
                    # 从元数据中删除
                    del file_metadata[file_url]
                    print(f"🗑️ 已删除元数据: {file_url}")
                
                # 从用户文件数据库中删除
                if file_url in user_files_db:
                    user_files_db.remove(file_url)
                    print(f"🗑️ 已从用户文件数据库删除: {file_url}")
                
                deleted_files.append(file_url)
                
            except Exception as e:
                error_msg = f"Failed to delete {file_key}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ 删除失败: {error_msg}")
        
        return jsonify({
            'statusCode': 200,
            'message': f'Successfully deleted {len(deleted_files)} files',
            'deleted_files': deleted_files,
            'errors': errors if errors else None,
            'total_deleted': len(deleted_files)
        })
        
    except Exception as e:
        print(f"❌ 删除操作出错: {str(e)}")
        return jsonify({'error': str(e)}), 500

def send_notification_email(email, species, filename, detection_result):
    """发送通知邮件 (模拟实现)"""
    notification = {
        'id': str(uuid.uuid4()),
        'email': email,
        'species': species,
        'filename': filename,
        'detection_result': detection_result,
        'timestamp': datetime.datetime.now().isoformat(),
        'type': 'bird_detection',
        'status': 'sent'
    }
    
    notification_history.append(notification)
    print(f"📧 发送通知邮件: {email} - 检测到 {species} 在文件 {filename}")
    return notification

def trigger_notifications(species, filename, detection_result):
    """当检测到鸟类时触发通知"""
    triggered_notifications = []
    
    # 查找订阅了此物种的用户
    for email, subscriptions in notification_subscriptions.items():
        if species.lower() in [sub.lower() for sub in subscriptions]:
            notification = send_notification_email(email, species, filename, detection_result)
            triggered_notifications.append(notification)
    
    return triggered_notifications

# 通知相关API端点
@app.route('/api/v1/subscribe', methods=['POST'])
def subscribe_notification():
    """订阅鸟类检测通知"""
    try:
        data = request.get_json()
        email = data.get('email')
        species = data.get('species')
        
        if not email or not species:
            return jsonify({'error': 'Email and species are required'}), 400
        
        # 初始化用户订阅列表
        if email not in notification_subscriptions:
            notification_subscriptions[email] = []
        
        # 添加物种订阅 (避免重复)
        species_lower = species.lower()
        if species_lower not in [sub.lower() for sub in notification_subscriptions[email]]:
            notification_subscriptions[email].append(species)
        
        return jsonify({
            'statusCode': 200,
            'message': f'Successfully subscribed to {species} notifications',
            'email': email,
            'species': species,
            'total_subscriptions': len(notification_subscriptions[email])
        })
        
    except Exception as e:
        print(f"❌ 订阅失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/unsubscribe', methods=['POST'])
def unsubscribe_notification():
    """取消订阅鸟类检测通知"""
    try:
        data = request.get_json()
        email = data.get('email')
        species = data.get('species')
        
        if not email or not species:
            return jsonify({'error': 'Email and species are required'}), 400
        
        if email not in notification_subscriptions:
            return jsonify({'error': 'No subscriptions found for this email'}), 404
        
        # 移除物种订阅
        species_lower = species.lower()
        notification_subscriptions[email] = [
            sub for sub in notification_subscriptions[email] 
            if sub.lower() != species_lower
        ]
        
        # 如果没有订阅了，删除用户记录
        if not notification_subscriptions[email]:
            del notification_subscriptions[email]
        
        return jsonify({
            'statusCode': 200,
            'message': f'Successfully unsubscribed from {species} notifications',
            'email': email,
            'species': species
        })
        
    except Exception as e:
        print(f"❌ 取消订阅失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/subscriptions', methods=['GET'])
def get_subscriptions():
    """获取用户的通知订阅"""
    try:
        email = request.args.get('email')
        
        if not email:
            return jsonify({'error': 'Email parameter is required'}), 400
        
        subscriptions = notification_subscriptions.get(email, [])
        
        return jsonify({
            'statusCode': 200,
            'email': email,
            'subscriptions': subscriptions,
            'total_subscriptions': len(subscriptions)
        })
        
    except Exception as e:
        print(f"❌ 获取订阅失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/notifications/history', methods=['GET'])
def get_notification_history():
    """获取通知历史"""
    try:
        email = request.args.get('email')
        limit = int(request.args.get('limit', 50))
        
        filtered_history = notification_history
        if email:
            filtered_history = [n for n in notification_history if n['email'] == email]
        
        # 按时间倒序排列，限制数量
        sorted_history = sorted(filtered_history, key=lambda x: x['timestamp'], reverse=True)[:limit]
        
        return jsonify({
            'statusCode': 200,
            'notifications': sorted_history,
            'total_count': len(filtered_history),
            'returned_count': len(sorted_history)
        })
        
    except Exception as e:
        print(f"❌ 获取通知历史失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/v1/notifications/stats', methods=['GET'])
def get_notification_stats():
    """获取通知统计信息"""
    try:
        total_subscriptions = sum(len(subs) for subs in notification_subscriptions.values())
        unique_emails = len(notification_subscriptions)
        total_notifications_sent = len(notification_history)
        
        # 统计各物种的订阅数量
        species_stats = {}
        for subscriptions in notification_subscriptions.values():
            for species in subscriptions:
                species_stats[species] = species_stats.get(species, 0) + 1
        
        return jsonify({
            'statusCode': 200,
            'stats': {
                'total_subscriptions': total_subscriptions,
                'unique_subscribers': unique_emails,
                'total_notifications_sent': total_notifications_sent,
                'species_subscription_counts': species_stats,
                'recent_notifications': len([n for n in notification_history 
                                           if (datetime.datetime.now() - datetime.datetime.fromisoformat(n['timestamp'])).days <= 7])
            }
        })
        
    except Exception as e:
        print(f"❌ 获取通知统计失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 启动BirdTag简化测试服务器...")
    print("📁 前端: http://localhost:8080")
    print("🔌 API: http://localhost:8080/api/*") 
    print("🐦 鸟类检测: Docker容器 localhost:9000")
    print("👤 认证系统: 已启用")
    
    app.run(host='0.0.0.0', port=8080, debug=True) 