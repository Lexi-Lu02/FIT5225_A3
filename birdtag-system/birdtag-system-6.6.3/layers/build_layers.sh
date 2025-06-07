#!/bin/bash

# 设置错误处理
set -e
trap 'echo "Error occurred at line $LINENO. Command: $BASH_COMMAND"' ERR

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Python 版本
check_python_version() {
    local version=$1
    if ! command -v python$version &> /dev/null; then
        log_error "Python $version is not installed"
        exit 1
    fi
}

# 检查目录是否存在
check_directory() {
    if [ ! -d "$1" ]; then
        log_error "Directory $1 does not exist"
        exit 1
    fi
}

# 主函数
main() {
    log_info "Starting layer build process..."

    # 检查 Python 版本
    check_python_version "3.9"
    check_python_version "3.11"

    # 创建临时目录
    log_info "Creating temporary directories..."
    mkdir -p temp_layers

    # 构建 Bird Detection Layer (Python 3.9)
    log_info "Building Bird Detection Layer..."
    mkdir -p temp_layers/bird_detection/python/lib/python3.9/site-packages
    python3.9 -m venv temp_layers/bird_detection/venv
    source temp_layers/bird_detection/venv/bin/activate
    
    log_info "Installing Bird Detection dependencies..."
    pip install --no-cache-dir -r layers/bird_detection/requirements.txt -t temp_layers/bird_detection/python/lib/python3.9/site-packages
    deactivate

    # 构建 BirdNET-Analyzer Layer (Python 3.11)
    log_info "Building BirdNET-Analyzer Layer..."
    mkdir -p temp_layers/birdnet_analyzer/python/lib/python3.11/site-packages
    python3.11 -m venv temp_layers/birdnet_analyzer/venv
    source temp_layers/birdnet_analyzer/venv/bin/activate
    
    log_info "Installing BirdNET-Analyzer dependencies..."
    pip install --no-cache-dir -r layers/birdnet_analyzer/requirements.txt -t temp_layers/birdnet_analyzer/python/lib/python3.11/site-packages
    deactivate

    # 检查模型文件
    log_info "Checking model files..."
    check_directory "layers/bird_detection/model"
    check_directory "layers/birdnet_analyzer/model"

    # 构建 FFmpeg Layer
    log_info "Building FFmpeg Layer..."
    check_directory "layers/ffmpeg/opt/ffmpeg"
    if [ ! -f "layers/ffmpeg/opt/ffmpeg/ffmpeg" ]; then
        log_error "FFmpeg binary not found in layers/ffmpeg/opt/ffmpeg/"
        exit 1
    fi
    chmod +x layers/ffmpeg/opt/ffmpeg/ffmpeg

    # 复制到 layers 目录
    log_info "Copying layers to final location..."
    cp -r temp_layers/bird_detection/python/* layers/bird_detection/python/
    cp -r temp_layers/birdnet_analyzer/python/* layers/birdnet_analyzer/python/

    # 清理临时目录
    log_info "Cleaning up..."
    rm -rf temp_layers

    log_info "Layer build complete!"
}

# 运行主函数
main 