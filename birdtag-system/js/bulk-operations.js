// Bulk Operations Module
function updateSelectedFiles() {
    const checkboxes = document.querySelectorAll('#searchResults input[type="checkbox"]:checked');
    selectedFiles = new Set(Array.from(checkboxes).map(cb => cb.value));
    
    document.getElementById('selectedFilesInfo').innerHTML = `
        <span class="badge bg-secondary">${selectedFiles.size} files selected</span>
    `;
}

function selectAllResults() {
    document.querySelectorAll('#searchResults input[type="checkbox"]').forEach(cb => {
        cb.checked = true;
    });
    updateSelectedFiles();
}

function deselectAllResults() {
    document.querySelectorAll('#searchResults input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
    updateSelectedFiles();
}

async function bulkAddTags() {
    if (!checkAuth()) return;
    
    const species = document.getElementById('bulkTagSpecies').value;
    const count = document.getElementById('bulkTagCount').value;
    
    if (!species || selectedFiles.size === 0) {
        showToast('Please select files and specify tags', 'warning');
        return;
    }
    
    await bulkTagOperation(1, species, count);
}

async function bulkRemoveTags() {
    if (!checkAuth()) return;
    
    const species = document.getElementById('bulkTagSpecies').value;
    const count = document.getElementById('bulkTagCount').value;
    
    if (!species || selectedFiles.size === 0) {
        showToast('Please select files and specify tags', 'warning');
        return;
    }
    
    await bulkTagOperation(0, species, count);
}

async function bulkTagOperation(operation, species, count) {
    showLoading(true);
    
    try {
        const response = await fetch(`${config.apiGatewayUrl}/v1/tags/update`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: Array.from(selectedFiles),
                operation: operation,
                tags: [`${species},${count}`]
            })
        });
        
        if (!response.ok) throw new Error('Tag update failed');
        
        showToast(`Tags ${operation === 1 ? 'added' : 'removed'} successfully!`, 'success');
        
        // Clear selections
        deselectAllResults();
        document.getElementById('bulkTagSpecies').value = '';
        document.getElementById('bulkTagCount').value = 1;
        
    } catch (error) {
        console.error('Tag operation error:', error);
        showToast('Failed to update tags: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function bulkDeleteFiles() {
    if (!checkAuth()) return;
    
    if (selectedFiles.size === 0) {
        showToast('Please select files to delete', 'warning');
        return;
    }
    
    if (!confirm(`Are you sure you want to delete ${selectedFiles.size} files? This cannot be undone.`)) {
        return;
    }
    
    showLoading(true);
    
    try {
        // Extract file keys from URLs
        const fileKeys = Array.from(selectedFiles).map(url => {
            const parts = url.split('.amazonaws.com/');
            return parts.length > 1 ? parts[1] : url;
        });
        
        const response = await fetch(`${config.apiGatewayUrl}/v1/files/delete`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fileKeys: fileKeys
            })
        });
        
        if (!response.ok) throw new Error('Delete failed');
        
        showToast(`${selectedFiles.size} files deleted successfully!`, 'success');
        
        // Remove deleted items from display
        document.querySelectorAll('#searchResults input[type="checkbox"]:checked').forEach(cb => {
            cb.closest('.thumbnail-container').remove();
        });
        
        selectedFiles.clear();
        updateSelectedFiles();
        
    } catch (error) {
        console.error('Delete error:', error);
        showToast('Failed to delete files: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}