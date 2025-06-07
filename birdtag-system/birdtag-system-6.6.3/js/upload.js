// File Upload Module
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

async function handleFiles(files) {
    if (!checkAuth()) return;
    
    document.getElementById('uploadQueue').style.display = 'block';
    const uploadList = document.getElementById('uploadList');
    uploadList.innerHTML = '';
    
    for (let file of files) {
        const fileId = 'file-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
        const fileHtml = `
            <div class="file-item" id="${fileId}">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="bi bi-file-earmark me-2"></i>
                        <span>${file.name}</span>
                        <small class="text-muted ms-2">(${formatFileSize(file.size)})</small>
                    </div>
                    <div>
                        <span class="upload-status badge bg-warning">Pending</span>
                    </div>
                </div>
                <div class="progress mt-2" style="height: 5px;">
                    <div class="progress-bar" role="progressbar" style="width: 0%"></div>
                </div>
            </div>
        `;
        uploadList.insertAdjacentHTML('beforeend', fileHtml);
        
        await uploadFile(file, fileId);
    }
}

async function uploadFile(file, fileId) {
    const fileElement = document.getElementById(fileId);
    const statusElement = fileElement.querySelector('.upload-status');
    const progressBar = fileElement.querySelector('.progress-bar');
    
    try {
        statusElement.textContent = 'Getting URL...';
        statusElement.className = 'upload-status badge bg-info';
        
        // Get presigned URL
        const response = await fetch(`${config.apiGatewayUrl}/upload/presign?filename=${encodeURIComponent(file.name)}`, {
            headers: {
                'Authorization': localStorage.getItem('idToken')
            }
        });
        
        if (!response.ok) throw new Error('Failed to get upload URL');
        
        const data = await response.json();
        
        // Upload to S3
        statusElement.textContent = 'Uploading...';
        progressBar.style.width = '50%';
        
        const uploadResponse = await fetch(data.uploadUrl, {
            method: 'PUT',
            body: file,
            headers: {
                'Content-Type': file.type
            }
        });
        
        if (!uploadResponse.ok) throw new Error('Upload failed');
        
        progressBar.style.width = '100%';
        statusElement.textContent = 'Complete';
        statusElement.className = 'upload-status badge bg-success';
        
        showToast(`${file.name} uploaded successfully!`, 'success');
        
    } catch (error) {
        console.error('Upload error:', error);
        statusElement.textContent = 'Failed';
        statusElement.className = 'upload-status badge bg-danger';
        showToast(`Failed to upload ${file.name}: ${error.message}`, 'danger');
    }
} 