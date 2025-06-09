// Search Module
let searchTimeout;
let currentSearchResults = [];

function setupSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    if (searchInput) {
        searchInput.addEventListener('input', debounceSearch);
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
    
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }
    
    // Filter buttons
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            performSearch();
        });
    });
    
    // Load initial media
    loadMediaFiles();
}

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(performSearch, 500);
}

async function performSearch() {
    const token = config.isLocalTesting ? 
        localStorage.getItem('authToken') : 
        localStorage.getItem('idToken');
        
    if (!token) {
        showToast('Please login first', 'error');
        return;
    }
    
    const searchInput = document.getElementById('searchInput');
    const query = searchInput ? searchInput.value.trim() : '';
    const activeFilter = document.querySelector('.filter-btn.active');
    const fileType = activeFilter ? activeFilter.getAttribute('data-filter') : '';
    
    try {
        showLoading(true);
        
        const authHeader = config.isLocalTesting ? 
            `Bearer ${token}` : 
            token;
            
        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (fileType && fileType !== 'all') params.append('file_type', fileType);
        params.append('limit', '50');
        
        const response = await fetch(`${config.apiGatewayUrl}/search?${params}`, {
            headers: {
                'Authorization': authHeader
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentSearchResults = data.results;
            displaySearchResults(data.results, query);
            
            // Update result count
            const resultCount = document.getElementById('resultCount');
            if (resultCount) {
                resultCount.textContent = `${data.results.length} results found`;
            }
        } else {
            const errorData = await response.json();
            showToast(errorData.message || 'Search failed', 'error');
        }
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed - server error', 'error');
    } finally {
        showLoading(false);
    }
}

function displaySearchResults(results, query = '') {
    const container = document.getElementById('searchResults') || document.getElementById('mediaContainer') || document.getElementById('galleryContainer');
    if (!container) return;
    
    if (results.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-5">
                <i class="bi bi-search fs-1 mb-3"></i>
                <h4>No results found</h4>
                <p>${query ? `No media found for "${query}"` : 'Try uploading some media files first'}</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = results.map(media => createMediaCard(media, query)).join('');
    
    // Add click handlers for media items
    container.querySelectorAll('.media-card').forEach(card => {
        card.addEventListener('click', () => {
            const mediaId = card.getAttribute('data-media-id');
            showMediaModal(mediaId);
        });
    });
}

function createMediaCard(media, searchQuery = '') {
    const createdDate = new Date(media.created_at).toLocaleDateString();
    const detectedSpecies = media.detected_species || [];
    
    // Highlight search terms in species names
    const highlightedSpecies = detectedSpecies.map(species => {
        if (searchQuery && species.toLowerCase().includes(searchQuery.toLowerCase())) {
            return species.replace(new RegExp(searchQuery, 'gi'), `<mark>$&</mark>`);
        }
        return species;
    });
    
    return `
        <div class="media-card thumbnail-container" data-media-id="${media.id}">
            <div class="media-preview">
                ${getMediaPreview(media)}
            </div>
            <div class="media-info thumbnail-overlay">
                <div class="media-title fw-bold">${media.original_name}</div>
                <div class="species-tags mb-2">
                    ${highlightedSpecies.map(species => `<span class="tag-chip">${species}</span>`).join('')}
                </div>
                <div class="media-meta">
                    <small class="text-light">
                        <i class="bi bi-calendar me-1"></i>${createdDate}
                        <i class="bi bi-file-earmark ms-2 me-1"></i>${media.file_type}
                    </small>
                </div>
                ${media.detection_boxes && media.detection_boxes.length > 0 ? 
                    `<div class="detection-info">
                        <small class="text-light">
                            <i class="bi bi-eye me-1"></i>${media.detection_boxes.length} detection(s)
                        </small>
                    </div>` : ''
                }
            </div>
        </div>
    `;
}

function getMediaPreview(media) {
    // Create URL for media based on environment
    let mediaUrl;
    if (config.isLocalTesting && media.s3_path.startsWith('uploads/')) {
        mediaUrl = `${config.apiGatewayUrl}/${media.s3_path}`;
    } else {
        mediaUrl = media.s3_path;
    }
    
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

async function showMediaModal(mediaId) {
    // Implementation for showing media modal
    console.log('Showing modal for media:', mediaId);
    showToast('Media modal functionality to be implemented', 'info');
}

// Legacy search functions from original code
function addSearchTag() {
    const species = document.getElementById('speciesSelect').value;
    const count = document.getElementById('countInput').value;
    
    if (!species) {
        showToast('Please select a species', 'warning');
        return;
    }
    
    const tagHtml = `
        <div class="search-tag">
            ${species}: ${count}
            <button onclick="this.parentElement.remove()">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `;
    
    document.getElementById('searchTags').insertAdjacentHTML('beforeend', tagHtml);
    document.getElementById('speciesSelect').value = '';
    document.getElementById('countInput').value = 1;
}

async function searchByTags() {
    if (!checkAuth()) return;
    
    const tags = {};
    document.querySelectorAll('.search-tag').forEach(tag => {
        const [species, count] = tag.textContent.trim().split(':');
        tags[species.trim()] = parseInt(count);
    });
    
    if (Object.keys(tags).length === 0) {
        showToast('Please add at least one tag', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${config.apiGatewayUrl}/v1/search`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(tags)
        });
        
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        displaySearchResults(data.results || data.links || []);
        
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function searchBySpeciesOnly() {
    if (!checkAuth()) return;
    
    const species = document.getElementById('speciesOnlySelect').value;
    if (!species) {
        showToast('Please select a species', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const searchCriteria = {};
        searchCriteria[species] = 1; // At least one
        
        const response = await fetch(`${config.apiGatewayUrl}/v1/search`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(searchCriteria)
        });
        
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        displaySearchResults(data.results || data.links || []);
        
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function searchByFile() {
    if (!checkAuth()) return;
    
    const fileInput = document.getElementById('searchFileInput');
    const file = fileInput.files[0];
    
    if (!file) {
        showToast('Please select a file', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${config.apiGatewayUrl}/v1/search-by-file`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken')
            },
            body: formData
        });
        
        if (!response.ok) throw new Error('Search failed');
        
        const data = await response.json();
        displaySearchResults(data.results || data.links || []);
        
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function resolveToOriginal() {
    if (!checkAuth()) return;
    
    const thumbnailUrl = document.getElementById('thumbnailUrl').value.trim();
    if (!thumbnailUrl) {
        showToast('Please enter a thumbnail URL', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${config.apiGatewayUrl}/v1/resolve`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ thumbnailUrl: thumbnailUrl })
        });
        
        if (!response.ok) throw new Error('Resolution failed');
        
        const data = await response.json();
        
        // Display the original URL
        const modal = new bootstrap.Modal(document.getElementById('imageModal'));
        document.getElementById('fullImage').src = data.originalUrl;
        document.getElementById('downloadLink').href = data.originalUrl;
        modal.show();
        
    } catch (error) {
        console.error('Resolve error:', error);
        showToast('Failed to resolve thumbnail: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function showFullImage(url, isThumbnail) {
    if (isThumbnail && checkAuth()) {
        // If it's a thumbnail, resolve to original first
        showLoading(true);
        try {
            const response = await fetch(`${config.apiGatewayUrl}/v1/resolve`, {
                method: 'POST',
                headers: {
                    'Authorization': localStorage.getItem('idToken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ thumbnailUrl: url })
            });
            
            if (response.ok) {
                const data = await response.json();
                url = data.originalUrl;
            }
        } catch (error) {
            console.error('Failed to resolve thumbnail:', error);
        } finally {
            showLoading(false);
        }
    }
    
    const modal = new bootstrap.Modal(document.getElementById('imageModal'));
    document.getElementById('fullImage').src = url;
    document.getElementById('downloadLink').href = url;
    modal.show();
} 