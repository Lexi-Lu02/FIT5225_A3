// Bulk Operations Module
function updateSelectedFiles() {
    const checkboxes = document.querySelectorAll('#searchResults input[type="checkbox"]:checked');
    selectedFiles = new Set(Array.from(checkboxes).map(cb => cb.value));
    
    // 更新选中文件的信息显示
    const selectedInfo = document.getElementById('selectedFilesInfo');
    if (selectedInfo) {
        const fileText = selectedFiles.size === 1 ? 'file' : 'files';
        selectedInfo.innerHTML = `
            <span class="badge bg-secondary">${selectedFiles.size} ${fileText} selected</span>
        `;
    }
    
    // 为选中的媒体卡片添加视觉效果
    document.querySelectorAll('#searchResults .media-card').forEach(card => {
        const checkbox = card.querySelector('input[type="checkbox"]');
        if (checkbox && checkbox.checked) {
            card.classList.add('selected');
        } else {
            card.classList.remove('selected');
        }
    });
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
    const count = document.getElementById('bulkTagCount').value || 1;
    
    if (!species || selectedFiles.size === 0) {
        showToast('Please select files and specify species', 'warning');
        return;
    }
    
    await bulkTagOperation('add', species, count);
}

async function bulkRemoveTags() {
    if (!checkAuth()) return;
    
    const species = document.getElementById('bulkTagSpecies').value;
    const count = document.getElementById('bulkTagCount').value || 1;
    
    if (!species || selectedFiles.size === 0) {
        showToast('Please select files and specify species', 'warning');
        return;
    }
    
    await bulkTagOperation('remove', species, count);
}

async function bulkTagOperation(operation, species, count) {
    showLoading(true);
    
    try {
        let successCount = 0;
        let errorCount = 0;
        
        // 为每个选中的文件执行标签操作
        for (const fileUrl of selectedFiles) {
            try {
                const endpoint = operation === 'add' ? '/tags/add' : '/tags/remove';
                const response = await fetch(`${config.apiGatewayUrl}${endpoint}`, {
                    method: 'POST',
                    headers: {
                        'Authorization': config.isLocalTesting ? 
                            `Bearer ${localStorage.getItem('authToken')}` : 
                            localStorage.getItem('idToken'),
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_url: fileUrl,
                        species: species,
                        count: parseInt(count)
                    })
                });
                
                if (response.ok) {
                    successCount++;
                } else {
                    errorCount++;
                    console.error(`Failed to ${operation} tags for ${fileUrl}`);
                }
            } catch (error) {
                errorCount++;
                console.error(`Error ${operation}ing tags for ${fileUrl}:`, error);
            }
        }
        
        if (successCount > 0) {
            const fileText = successCount === 1 ? 'file' : 'files';
            showToast(`Successfully ${operation}ed tags for ${successCount} ${fileText}!`, 'success');
        }
        
        if (errorCount > 0) {
            const fileText = errorCount === 1 ? 'file' : 'files';
            showToast(`Failed to ${operation} tags for ${errorCount} ${fileText}`, 'warning');
        }
        
        // Clear selections
        deselectAllResults();
        document.getElementById('bulkTagSpecies').value = '';
        document.getElementById('bulkTagCount').value = 1;
        
        // 刷新搜索结果
        if (typeof performSearch === 'function') {
            setTimeout(performSearch, 500);
        }
        
    } catch (error) {
        console.error('Bulk tag operation error:', error);
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
    
    const fileText = selectedFiles.size === 1 ? 'file' : 'files';
    if (!confirm(`Are you sure you want to delete ${selectedFiles.size} ${fileText}? This cannot be undone.`)) {
        return;
    }
    
    showLoading(true);
    
    try {
        // 对于本地测试，直接使用文件URL作为fileKeys
        const fileKeys = Array.from(selectedFiles);
        
        const response = await fetch(`${config.apiGatewayUrl}/v1/files/delete`, {
            method: 'POST',
            headers: {
                'Authorization': config.isLocalTesting ? 
                    `Bearer ${localStorage.getItem('authToken')}` : 
                    localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fileKeys: fileKeys
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || 'Delete failed');
        }
        
        const data = await response.json();
        const deletedCount = data.total_deleted || selectedFiles.size;
        const fileText = deletedCount === 1 ? 'file' : 'files';
        showToast(`Successfully deleted ${deletedCount} ${fileText}!`, 'success');
        
        // Remove deleted items from display
        document.querySelectorAll('#searchResults input[type="checkbox"]:checked').forEach(cb => {
            cb.closest('.media-card').remove();
        });
        
        // For my files page
        document.querySelectorAll('#myFilesList input[type="checkbox"]:checked').forEach(cb => {
            cb.closest('.file-item').remove();
        });
        
        selectedFiles.clear();
        updateSelectedFiles();
        
        // 刷新搜索结果
        if (typeof performSearch === 'function') {
            setTimeout(performSearch, 500);
        }
        
    } catch (error) {
        console.error('Delete error:', error);
        showToast('Failed to delete files: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}