// Search Module
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

function displaySearchResults(urls) {
    const resultsContainer = document.getElementById('searchResults');
    const resultsInfo = document.getElementById('searchResultsInfo');
    
    if (!urls || urls.length === 0) {
        resultsContainer.innerHTML = '<p class="text-muted w-100 text-center">No results found</p>';
        resultsInfo.innerHTML = '';
        return;
    }
    
    resultsInfo.innerHTML = `<div class="alert alert-info">Found ${urls.length} results</div>`;
    resultsContainer.innerHTML = '';
    
    urls.forEach((url, index) => {
        const isVideo = url.includes('.mp4') || url.includes('.avi') || url.includes('.mov');
        const isAudio = url.includes('.mp3') || url.includes('.wav');
        const isThumbnail = url.includes('thumbnail') || url.includes('thumb');
        
        let content = '';
        if (isVideo) {
            content = `
                <div class="text-center p-3">
                    <i class="bi bi-camera-video" style="font-size: 3rem;"></i>
                    <p class="mt-2">Video File</p>
                    <a href="${url}" class="btn btn-sm btn-primary" download>
                        <i class="bi bi-download"></i> Download
                    </a>
                </div>
            `;
        } else if (isAudio) {
            content = `
                <div class="text-center p-3">
                    <i class="bi bi-music-note-beamed" style="font-size: 3rem;"></i>
                    <p class="mt-2">Audio File</p>
                    <audio controls class="w-100">
                        <source src="${url}" type="audio/mpeg">
                    </audio>
                </div>
            `;
        } else {
            content = `
                <img src="${url}" class="thumbnail" alt="Result ${index + 1}" 
                     onclick="showFullImage('${url}', ${isThumbnail})">
                <div class="thumbnail-overlay">
                    <small>Click to ${isThumbnail ? 'get original' : 'preview'}</small>
                </div>
            `;
        }
        
        const html = `
            <div class="thumbnail-container">
                <input type="checkbox" class="form-check-input position-absolute top-0 start-0 m-2" 
                       value="${url}" onchange="updateSelectedFiles()">
                ${content}
            </div>
        `;
        
        resultsContainer.insertAdjacentHTML('beforeend', html);
    });
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