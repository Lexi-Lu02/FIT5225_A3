// File Upload Module
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    
    if (!dropZone || !fileInput) return;
    
    // Click to upload
    dropZone.addEventListener('click', () => fileInput.click());
    
    // Drag and drop events
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
        const files = e.dataTransfer.files;
        handleFiles(files);
    });
    
    // File input change
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });
}

async function handleFiles(files) {
    if (!files.length) return;
    
    // Check authentication based on environment
    const token = config.isLocalTesting ? 
        localStorage.getItem('authToken') : 
        localStorage.getItem('idToken');
        
    if (!token) {
        showToast('Please login first', 'error');
        return;
    }
    
    for (let file of files) {
        if (validateFile(file)) {
            await uploadFile(file);
        }
    }
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        showToast(`Uploading ${file.name}...`, 'info');
        showLoading(true);
        
        const token = config.isLocalTesting ? 
            localStorage.getItem('authToken') : 
            localStorage.getItem('idToken');
            
        const authHeader = config.isLocalTesting ? 
            `Bearer ${token}` : 
            token;
        
        const response = await fetch(`${config.apiGatewayUrl}/upload`, {
            method: 'POST',
            headers: {
                'Authorization': authHeader
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`${file.name} uploaded successfully!`, 'success');
            
            // Simulate processing delay for local testing
            if (config.isLocalTesting) {
                setTimeout(() => {
                    showToast(`Analysis complete for ${file.name}. Species detected: ${data.data.detected_species.join(', ')}`, 'success');
                    // Refresh the media display
                    if (typeof loadMediaFiles === 'function') {
                        loadMediaFiles();
                    }
                }, 2000);
            } else {
                // For production, refresh immediately
                if (typeof loadMediaFiles === 'function') {
                    loadMediaFiles();
                }
            }
        } else {
            showToast(`Upload failed: ${data.message}`, 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast(`Upload failed: ${error.message}`, 'error');
    } finally {
        showLoading(false);
    }
}

// File validation
function validateFile(file) {
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedTypes = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif',
        'video/mp4', 'video/avi', 'video/mov', 'video/quicktime',
        'audio/wav', 'audio/mp3', 'audio/m4a'
    ];
    
    if (file.size > maxSize) {
        showToast('File size exceeds 100MB limit', 'error');
        return false;
    }
    
    if (!allowedTypes.includes(file.type)) {
        showToast('File type not supported', 'error');
        return false;
    }
    
    return true;
}

// Load user's media files
async function loadMediaFiles() {
    const token = config.isLocalTesting ? 
        localStorage.getItem('authToken') : 
        localStorage.getItem('idToken');
        
    if (!token) return;
    
    try {
        const authHeader = config.isLocalTesting ? 
            `Bearer ${token}` : 
            token;
            
        const response = await fetch(`${config.apiGatewayUrl}/media`, {
            headers: {
                'Authorization': authHeader
            }
        });
        
        if (response.ok) {
            const media = await response.json();
            displayMediaFiles(media);
        } else {
            console.error('Failed to load media files');
        }
    } catch (error) {
        console.error('Error loading media files:', error);
    }
}

function displayMediaFiles(mediaList) {
    // Try to find any available container for displaying media files
    const container = document.getElementById('myFilesList') || 
                     document.getElementById('mediaContainer') || 
                     document.getElementById('galleryContainer') ||
                     document.getElementById('searchResults');
    
    if (!container) {
        console.error('No container found for displaying media files');
        return;
    }
    
    console.log(`Displaying ${mediaList.length} media files`);
    
    if (mediaList.length === 0) {
        container.innerHTML = '<div class="text-center text-muted py-4">No media files uploaded yet.</div>';
        return;
    }
    
    container.innerHTML = mediaList.map(media => {
        // Create URL for media based on environment
        let mediaUrl;
        if (config.isLocalTesting && media.s3_path.startsWith('uploads/')) {
            mediaUrl = `${config.apiGatewayUrl}/${media.s3_path}`;
        } else {
            mediaUrl = media.s3_path;
        }
            
        return `
            <div class="thumbnail-container" data-media-id="${media.id}">
                ${getMediaPreview(media, mediaUrl)}
                <div class="thumbnail-overlay">
                    <div class="fw-bold">${media.original_name}</div>
                    <div class="species-tags mb-1">
                        ${media.detected_species.map(species => `<span class="tag-chip">${species}</span>`).join('')}
                    </div>
                    <small class="text-light">
                        <i class="bi bi-calendar me-1"></i>${new Date(media.created_at).toLocaleDateString()}
                        <br>
                        <i class="bi bi-file-earmark me-1"></i>${media.file_type}
                    </small>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click handlers for media items
    container.querySelectorAll('.thumbnail-container').forEach(item => {
        item.addEventListener('click', () => {
            const mediaId = item.getAttribute('data-media-id');
            showMediaDetails(mediaId);
        });
    });
}

function getMediaPreview(media, mediaUrl) {
    switch (media.file_type) {
        case 'image':
            return `<img src="${mediaUrl}" alt="${media.original_name}" class="thumbnail" 
                        onerror="this.src='https://via.placeholder.com/200x200?text=Image+Not+Found'">`;
        case 'video':
            return `
                <video class="thumbnail" poster="${media.thumbnail_path || ''}" muted>
                    <source src="${mediaUrl}" type="video/mp4">
                </video>
                <div class="media-type-overlay">
                    <i class="bi bi-play-circle-fill"></i>
                </div>
            `;
        case 'audio':
            return `
                <div class="audio-placeholder thumbnail">
                    <i class="bi bi-music-note-beamed"></i>
                    <div>Audio</div>
                    <small>${media.original_name}</small>
                </div>
            `;
        default:
            return `
                <div class="unknown-placeholder thumbnail">
                    <i class="bi bi-file-earmark"></i>
                    <div>Unknown</div>
                </div>
            `;
    }
}

async function showMediaDetails(mediaId) {
    // Implementation for showing media details modal
    console.log('Showing details for media:', mediaId);
    showToast('Media details functionality to be implemented', 'info');
} 