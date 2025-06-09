// File Manager Module
async function loadMyFiles() {
    if (!checkAuth()) return;
    
    showLoading(true);
    const filesList = document.getElementById('myFilesList');
    
    try {
        // 使用正确的认证和API端点
        const token = config.isLocalTesting ? 
            localStorage.getItem('authToken') : 
            localStorage.getItem('idToken');
            
        const authHeader = config.isLocalTesting ? 
            `Bearer ${token}` : 
            token;
        
        // 使用媒体API获取文件列表
        const response = await fetch(`${config.apiGatewayUrl}/media`, {
            method: 'GET',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Failed to load files');
        
        const data = await response.json();
        const files = data.files || [];
        
        if (files.length === 0) {
            filesList.innerHTML = '<p class="text-muted text-center">No files uploaded yet</p>';
            return;
        }
        
        filesList.innerHTML = files.map((file, index) => {
            const fileName = file.filename || file.original_name || 'Unknown';
            const fileUrl = file.url || file.thumbnail || file.s3_path || '';
            const fileType = file.file_type || getFileType(fileUrl);
            const icon = getFileIcon(fileType);
            
            // 显示检测信息
            const detectionInfo = file.detected_species && file.detected_species.length > 0 ? 
                `<small class="text-success">
                    <i class="bi bi-check-circle"></i> 
                    Detected: ${file.detected_species.join(', ')}
                    ${file.confidence ? ` (${(file.confidence * 100).toFixed(1)}%)` : ''}
                    ${file.detection_segments && file.detection_segments.length > 0 ? 
                        ` - ${file.detection_segments.length} segments` : ''}
                    ${file.detected_objects && file.total_frames ? 
                        ` - ${file.detected_objects} objects in ${file.total_frames} frames` : ''}
                </small>` : 
                '<small class="text-muted">No birds detected</small>';
            
            return `
                <div class="file-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-center">
                                <input type="checkbox" class="form-check-input me-2" value="${fileUrl}">
                                <i class="${icon} me-2"></i>
                                <div>
                                    <div><strong>${fileName}</strong></div>
                                    ${detectionInfo}
                                    ${file.tags && file.tags.length > 0 ? 
                                        `<div class="mt-1">
                                            ${file.tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('')}
                                        </div>` : ''
                                    }
                                    <small class="text-muted">
                                        <i class="bi bi-calendar me-1"></i>
                                        ${file.upload_time ? new Date(file.upload_time).toLocaleDateString() : 'Unknown date'}
                                    </small>
                                </div>
                            </div>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewFile('${fileUrl}')">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-warning" onclick="editFileTags('${fileUrl}')">
                                <i class="bi bi-tags"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${fileUrl}')">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Load files error:', error);
        filesList.innerHTML = '<p class="text-danger text-center">Failed to load files</p>';
    } finally {
        showLoading(false);
    }
}

function refreshMyFiles() {
    loadMyFiles();
}

async function deleteSelectedFiles() {
    const checkboxes = document.querySelectorAll('#myFilesList input[type="checkbox"]:checked');
    const urls = Array.from(checkboxes).map(cb => cb.value);
    
    if (urls.length === 0) {
        showToast('Please select files to delete', 'warning');
        return;
    }
    
    const fileText = urls.length === 1 ? 'file' : 'files';
    if (!confirm(`Delete ${urls.length} ${fileText}?`)) return;
    
    selectedFiles = new Set(urls);
    await bulkDeleteFiles();
    loadMyFiles();
}

async function deleteFile(url) {
    if (!confirm('Delete this file?')) return;
    
    selectedFiles = new Set([url]);
    await bulkDeleteFiles();
    loadMyFiles();
}

function viewFile(url) {
    const fileType = getFileType(url);
    
    if (fileType === 'image') {
        showImageWithDetection(url);
    } else if (fileType === 'video') {
        // 在专门的视频播放页面中打开视频
        const filename = url.split('/').pop();
        const videoPlayerUrl = `/video-player.html?url=${encodeURIComponent(url)}&filename=${encodeURIComponent(filename)}`;
        window.open(videoPlayerUrl, '_blank');
    } else if (fileType === 'audio') {
        showAudioInModal(url);
    } else {
        window.open(url, '_blank');
    }
}

function showVideoInModal(url) {
    const filename = url.split('/').pop();
    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    
    // Replace image with video
    const imageContainer = document.getElementById('fullImage').parentElement;
    imageContainer.innerHTML = `
        <video controls style="max-width: 100%; max-height: 500px;" autoplay>
            <source src="${url}" type="video/mp4">
            Your browser does not support the video tag.
        </video>
    `;
    
    document.getElementById('downloadLink').href = url;
    document.getElementById('imageMetadata').innerHTML = `
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0">🎥 视频文件</h6>
            </div>
            <div class="card-body">
                <strong>文件名:</strong> ${filename}<br>
                <small class="text-muted">点击外部区域关闭</small>
            </div>
        </div>
    `;
    
    modal.show();
    
    // Reset when modal closes
    modal._element.addEventListener('hidden.bs.modal', function() {
        imageContainer.innerHTML = '<img id="fullImage" class="img-fluid" style="max-height: 500px;" alt="Full size image">';
    }, { once: true });
}

function showAudioInModal(url) {
    const filename = url.split('/').pop();
    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    
    // Replace image with audio player
    const imageContainer = document.getElementById('fullImage').parentElement;
    imageContainer.innerHTML = `
        <div class="text-center p-4">
            <i class="bi bi-music-note-beamed" style="font-size: 4rem; color: #6c757d;"></i>
            <h5 class="mt-3">${filename}</h5>
            <audio controls class="mt-3" style="width: 100%;">
                <source src="${url}" type="audio/mpeg">
                <source src="${url}" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
        </div>
    `;
    
    document.getElementById('downloadLink').href = url;
    document.getElementById('imageMetadata').innerHTML = `
        <div class="card">
            <div class="card-header">
                <h6 class="mb-0">🎵 音频文件</h6>
            </div>
            <div class="card-body">
                <strong>文件名:</strong> ${filename}<br>
                <small class="text-muted">点击外部区域关闭</small>
            </div>
        </div>
    `;
    
    modal.show();
    
    // Reset when modal closes
    modal._element.addEventListener('hidden.bs.modal', function() {
        imageContainer.innerHTML = '<img id="fullImage" class="img-fluid" style="max-height: 500px;" alt="Full size image">';
    }, { once: true });
}

async function editFileTags(url) {
    currentFileUrl = url;
    const modal = new bootstrap.Modal(document.getElementById('tagModal'));
    
    // Load current tags and species list
    document.getElementById('currentTags').innerHTML = '<p class="text-muted">Loading tags...</p>';
    
    try {
        const filename = url.split('/').pop();
        
        // Load current file tags
        const tagsResponse = await fetch(`${config.apiGatewayUrl}/tags/${filename}`);
        if (tagsResponse.ok) {
            const tagsData = await tagsResponse.json();
            const tags = tagsData.tags || [];
            const detectedSpecies = tagsData.detected_species || [];
            
            document.getElementById('currentTags').innerHTML = `
                <div class="mb-3">
                    <strong>Current Tags:</strong>
                    <div class="mt-1">
                        ${tags.length > 0 ? 
                            tags.map(tag => `<span class="badge bg-secondary me-1">${tag}</span>`).join('') :
                            '<span class="text-muted">No tags yet</span>'
                        }
                    </div>
                </div>
                ${detectedSpecies.length > 0 ? `
                    <div class="mb-3">
                        <strong>Detected Species:</strong>
                        <div class="mt-1">
                            ${detectedSpecies.map(species => `<span class="badge bg-success me-1">${species}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            `;
        } else {
            document.getElementById('currentTags').innerHTML = '<p class="text-muted">Unable to load tag information</p>';
        }
        
        // Load species list for dropdown
        const speciesResponse = await fetch(`${config.apiGatewayUrl}/species`);
        if (speciesResponse.ok) {
            const speciesData = await speciesResponse.json();
            const speciesList = speciesData.species || [];
            
            const dropdown = document.getElementById('tagSpecies');
            dropdown.innerHTML = '<option value="">Select species...</option>' +
                speciesList.map(species => `<option value="${species.toLowerCase()}">${species}</option>`).join('');
        }
        
    } catch (error) {
        console.error('Error loading tags:', error);
        document.getElementById('currentTags').innerHTML = '<p class="text-danger">Error loading tags</p>';
    }
    
    modal.show();
}

async function modifyTags(operation) {
    if (!currentFileUrl) return;
    
    const species = document.getElementById('tagSpecies').value;
    const count = document.getElementById('tagCount').value || 1;
    
    if (!species) {
        showToast('Please select species', 'warning');
        return;
    }
    
    // 设置选中的文件
    selectedFiles = new Set([currentFileUrl]);
    
    // 调用批量操作函数
    const operationType = operation === 1 ? 'add' : 'remove';
    await bulkTagOperation(operationType, species, count);
    
    // 关闭模态框并刷新文件列表
    bootstrap.Modal.getInstance(document.getElementById('tagModal')).hide();
    refreshMyFiles();
}

function getFileType(url) {
    const ext = url.split('.').pop().toLowerCase();
    if (['jpg', 'jpeg', 'png', 'gif'].includes(ext)) return 'image';
    if (['mp4', 'avi', 'mov'].includes(ext)) return 'video';
    if (['mp3', 'wav'].includes(ext)) return 'audio';
    return 'other';
}

function getFileIcon(type) {
    switch (type) {
        case 'image': return 'bi bi-image';
        case 'video': return 'bi bi-camera-video';
        case 'audio': return 'bi bi-music-note-beamed';
        default: return 'bi bi-file-earmark';
    }
}

async function showImageWithDetection(url) {
    try {
        const filename = url.split('/').pop();
        
        const response = await fetch(`${config.apiGatewayUrl}/detection-result/${filename}`);
        let detectionInfo = null;
        
        if (response.ok) {
            const data = await response.json();
            detectionInfo = data.result;
        }
        
        const modal = new bootstrap.Modal(document.getElementById('imageModal'));
        document.getElementById('fullImage').src = url;
        document.getElementById('downloadLink').href = url;
        
        const metadataDiv = document.getElementById('imageMetadata');
        if (detectionInfo) {
            // 检查文件类型
            const isAudio = detectionInfo.detection_segments && detectionInfo.detection_segments.length > 0;
            const isVideo = detectionInfo.total_frames && detectionInfo.total_frames > 0;
            
            let fileTypeIcon = '🐦';
            if (isAudio) fileTypeIcon = '🎵';
            if (isVideo) fileTypeIcon = '🎞';
            
            metadataDiv.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h6 class="mb-0">${fileTypeIcon} Detection Results</h6>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-6">
                                <strong>Detection Status:</strong> 
                                ${getStatusBadge(detectionInfo.detection_status)}
                            </div>
                            <div class="col-6">
                                <strong>Upload Time:</strong> 
                                ${detectionInfo.upload_time ? new Date(detectionInfo.upload_time).toLocaleString() : 'N/A'}
                            </div>
                        </div>
                        ${detectionInfo.bird_detected ? `
                            <div class="mt-3">
                                <strong>Detected Species:</strong>
                                <div class="mt-1">
                                    ${detectionInfo.detected_species.map(species => 
                                        `<span class="badge bg-success me-1">${species}</span>`
                                    ).join('')}
                                </div>
                            </div>
                            ${detectionInfo.confidence ? `
                                <div class="mt-2">
                                    <strong>Confidence:</strong> ${(detectionInfo.confidence * 100).toFixed(1)}%
                                    <div class="progress mt-1" style="height: 6px;">
                                        <div class="progress-bar bg-success" style="width: ${detectionInfo.confidence * 100}%"></div>
                                    </div>
                                </div>
                            ` : ''}
                            ${detectionInfo.detection_boxes && detectionInfo.detection_boxes.length > 0 ? `
                                <div class="mt-2">
                                    <strong>Detection Boxes:</strong> ${detectionInfo.detection_boxes.length} regions
                                    ${isVideo ? `
                                        <div class="mt-2" style="max-height: 200px; overflow-y: auto;">
                                            ${detectionInfo.detection_boxes.map(box => `
                                                <div class="border rounded p-2 mb-1">
                                                    <strong>Frame ${box.frame || 'unknown'}</strong> 
                                                    <span class="badge bg-info">${box.timestamp || 0}s</span><br>
                                                    <small class="text-muted">
                                                        Box: ${box.x || 0}, ${box.y || 0}, ${box.width || 0}, ${box.height || 0}
                                                    </small>
                                                </div>
                                            `).join('')}
                                        </div>
                                    ` : ''}
                                </div>
                            ` : ''}
                            ${detectionInfo.detection_segments && detectionInfo.detection_segments.length > 0 ? `
                                <div class="mt-2">
                                    <strong>Audio Segments:</strong> ${detectionInfo.detection_segments.length} detections
                                    <div class="mt-2" style="max-height: 200px; overflow-y: auto;">
                                        ${detectionInfo.detection_segments.map(seg => `
                                            <div class="border rounded p-2 mb-1">
                                                <strong>${seg.species}</strong> 
                                                <span class="badge bg-primary">${(seg.confidence * 100).toFixed(1)}%</span><br>
                                                <small class="text-muted">
                                                    ${seg.start.toFixed(1)}s - ${seg.end.toFixed(1)}s
                                                    ${seg.code ? ` (${seg.code})` : ''}
                                                </small>
                                            </div>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}
                            ${isVideo ? `
                                <div class="mt-2">
                                    <strong>Video Analysis:</strong>
                                    <div class="mt-1">
                                        <span class="badge bg-secondary me-1">Frames: ${detectionInfo.total_frames}</span>
                                        <span class="badge bg-secondary me-1">Objects: ${detectionInfo.detected_objects || 0}</span>
                                        ${detectionInfo.video_duration ? 
                                            `<span class="badge bg-secondary">Duration: ~${detectionInfo.video_duration}s</span>` : ''}
                                    </div>
                                </div>
                            ` : ''}
                        ` : `
                            <div class="mt-3 text-muted">
                                <i class="bi bi-info-circle"></i> 
                                ${detectionInfo.detection_status === 'pending' ? 'Detection in progress...' : 
                                  detectionInfo.detection_status === 'failed' ? 'Detection failed' : 'No birds detected'}
                            </div>
                        `}
                        
                        ${detectionInfo.tags && detectionInfo.tags.length > 0 ? `
                            <div class="mt-3">
                                <strong>标签:</strong>
                                <div class="mt-1">
                                    ${detectionInfo.tags.map(tag => 
                                        `<span class="badge bg-secondary me-1">${tag}</span>`
                                    ).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        } else {
            metadataDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> 无法获取检测信息
                </div>
            `;
        }
        
        modal.show();
        
    } catch (error) {
        console.error('Error showing image with detection:', error);
        showFullImage(url, false);
    }
}

function getStatusBadge(status) {
    switch (status) {
        case 'completed':
            return '<span class="badge bg-success">检测完成</span>';
        case 'pending':
            return '<span class="badge bg-warning">检测中</span>';
        case 'failed':
            return '<span class="badge bg-danger">检测失败</span>';
        default:
            return '<span class="badge bg-secondary">未开始</span>';
    }
} 