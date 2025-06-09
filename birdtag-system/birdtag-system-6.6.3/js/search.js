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
    
    // Load initial media and species list
    loadMediaFiles();
    loadSpeciesList();
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
        
        // 使用POST请求调用/api/v1/search端点
        const response = await fetch(`${config.apiGatewayUrl}/v1/search`, {
            method: 'POST',
            headers: {
                'Authorization': authHeader,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                file_type: fileType || 'all'
            })
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
        showToast('Search failed: ' + error.message, 'error');
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
    
    // Add click handlers for media items (but prevent checkbox clicks from triggering modal)
    container.querySelectorAll('.media-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // 如果点击的是复选框或其容器，不打开模态框
            if (e.target.type === 'checkbox' || e.target.closest('.selection-checkbox')) {
                return;
            }
            
            const mediaId = card.getAttribute('data-media-id');
            showMediaModal(mediaId);
        });
    });
    
    // 确保复选框事件正常工作
    container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', function(e) {
            e.stopPropagation(); // 防止事件冒泡
            updateSelectedFiles();
        });
    });
    
    // 初始化选中状态显示
    if (typeof updateSelectedFiles === 'function') {
        updateSelectedFiles();
    }
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
    
    // Generate unique media URL for local testing
    const mediaUrl = media.s3_path || media.url || media.thumbnail || '';
    
    return `
        <div class="media-card thumbnail-container" data-media-id="${media.id}">
            <!-- 选择复选框 -->
            <div class="selection-checkbox">
                <input type="checkbox" class="form-check-input" value="${mediaUrl}" 
                       onchange="updateSelectedFiles()">
            </div>
            
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
    
    // 安全地处理s3_path，避免undefined错误
    const s3Path = media.s3_path || media.url || media.thumbnail || '';
    
    if (config.isLocalTesting && s3Path && s3Path.startsWith('uploads/')) {
        mediaUrl = `${config.apiGatewayUrl}/${s3Path}`;
    } else {
        mediaUrl = s3Path || media.url || media.thumbnail || '';
    }
    
    // 如果仍然没有有效的URL，使用占位符
    if (!mediaUrl) {
        mediaUrl = 'https://via.placeholder.com/200x200?text=No+Image';
    }
    
    const fileType = media.file_type || 'image';
    const mediaName = media.original_name || media.filename || 'Unknown';
    
    switch (fileType) {
        case 'image':
            return `<img src="${mediaUrl}" alt="${mediaName}" class="thumbnail" 
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
                    <small>${mediaName}</small>
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
    if (isThumbnail) {
        // Resolve thumbnail to original if needed
        try {
            const response = await fetch(`${config.apiGatewayUrl}/v1/resolve`, {
                method: 'POST',
                headers: {
                    'Authorization': localStorage.getItem('idToken'),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ thumbnail_url: url })
            });
            
            if (response.ok) {
                const data = await response.json();
                window.open(data.originalUrl, '_blank');
            } else {
                window.open(url, '_blank');
            }
        } catch (error) {
            window.open(url, '_blank');
        }
    } else {
        window.open(url, '_blank');
    }
}

// 添加缺失的loadMediaFiles函数
async function loadMediaFiles() {
    try {
        showLoading(true);
        
        // 调用搜索API获取所有媒体文件
        const response = await fetch(`${config.apiGatewayUrl}/v1/search`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({}) // 空查询返回所有文件
        });
        
        if (response.ok) {
            const data = await response.json();
            currentSearchResults = data.results;
            displaySearchResults(data.results);
            
            // Update result count
            const resultCount = document.getElementById('resultCount');
            if (resultCount) {
                resultCount.textContent = `${data.results.length} files found`;
            }
        } else {
            console.error('Failed to load media files');
            const container = document.getElementById('searchResults') || document.getElementById('mediaContainer');
            if (container) {
                container.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-exclamation-triangle fs-1 mb-3"></i>
                        <h4>Failed to load media files</h4>
                        <p>Please try refreshing the page</p>
                    </div>
                `;
            }
        }
    } catch (error) {
        console.error('Error loading media files:', error);
        const container = document.getElementById('searchResults') || document.getElementById('mediaContainer');
        if (container) {
            container.innerHTML = `
                <div class="text-center text-muted py-5">
                    <i class="bi bi-wifi-off fs-1 mb-3"></i>
                    <h4>Connection Error</h4>
                    <p>Please check your internet connection and try again</p>
                </div>
            `;
        }
    } finally {
        showLoading(false);
    }
}

// 加载可用物种列表到批量标签管理下拉框
async function loadSpeciesList() {
    try {
        const response = await fetch(`${config.apiGatewayUrl}/species`);
        if (response.ok) {
            const data = await response.json();
            const speciesSelect = document.getElementById('bulkTagSpecies');
            
            if (speciesSelect && data.species) {
                // 保留默认选项，添加物种列表
                speciesSelect.innerHTML = '<option value="">Select species...</option>' +
                    data.species.map(species => 
                        `<option value="${species.toLowerCase()}">${species}</option>`
                    ).join('');
            }
        }
    } catch (error) {
        console.error('Error loading species list:', error);
        // 如果加载失败，使用默认的物种列表
    }
}

// 确保在DOM加载后初始化搜索功能
document.addEventListener('DOMContentLoaded', function() {
    if (typeof setupSearch === 'function') {
        setupSearch();
    }
}); 