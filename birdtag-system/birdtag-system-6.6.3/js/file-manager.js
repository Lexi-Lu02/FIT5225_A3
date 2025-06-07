// File Manager Module
async function loadMyFiles() {
    if (!checkAuth()) return;
    
    showLoading(true);
    const filesList = document.getElementById('myFilesList');
    
    try {
        // Search for all files
        const response = await fetch(`${config.apiGatewayUrl}/v1/search`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({}) // Empty search returns all user's files
        });
        
        if (!response.ok) throw new Error('Failed to load files');
        
        const data = await response.json();
        const files = data.results || data.links || [];
        
        if (files.length === 0) {
            filesList.innerHTML = '<p class="text-muted text-center">No files uploaded yet</p>';
            return;
        }
        
        filesList.innerHTML = files.map((url, index) => {
            const fileName = url.split('/').pop();
            const fileType = getFileType(url);
            const icon = getFileIcon(fileType);
            
            return `
                <div class="file-item">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <input type="checkbox" class="form-check-input me-2" value="${url}">
                            <i class="${icon} me-2"></i>
                            <span>${fileName}</span>
                        </div>
                        <div>
                            <button class="btn btn-sm btn-outline-primary" onclick="viewFile('${url}')">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-warning" onclick="editFileTags('${url}')">
                                <i class="bi bi-tags"></i>
                            </button>
                            <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${url}')">
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
    
    if (!confirm(`Delete ${urls.length} files?`)) return;
    
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
        showFullImage(url, false);
    } else if (fileType === 'video' || fileType === 'audio') {
        window.open(url, '_blank');
    }
}

function editFileTags(url) {
    currentFileUrl = url;
    const modal = new bootstrap.Modal(document.getElementById('tagModal'));
    
    // Load current tags (this would need an API endpoint to get file metadata)
    document.getElementById('currentTags').innerHTML = '<p class="text-muted">Loading tags...</p>';
    
    modal.show();
}

async function modifyTags(operation) {
    if (!currentFileUrl) return;
    
    const species = document.getElementById('tagSpecies').value;
    const count = document.getElementById('tagCount').value;
    
    if (!species) {
        showToast('Please select species', 'warning');
        return;
    }
    
    selectedFiles = new Set([currentFileUrl]);
    await bulkTagOperation(operation, species, count);
    
    bootstrap.Modal.getInstance(document.getElementById('tagModal')).hide();
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