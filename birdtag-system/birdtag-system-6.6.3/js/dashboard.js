// Dashboard Module
async function loadDashboard() {
    if (!checkAuth()) return;
    
    try {
        // Load real media files from API
        const response = await fetch('/api/media');
        const data = await response.json();
        
        if (data.statusCode === 200 && data.files) {
            const files = data.files;
            
            // Update dashboard statistics with real data
            document.getElementById('totalFiles').textContent = files.length.toString();
            
            // Count unique detected species
            const allSpecies = new Set();
            files.forEach(file => {
                if (file.detected_species) {
                    file.detected_species.forEach(species => allSpecies.add(species));
                }
            });
            document.getElementById('totalTags').textContent = allSpecies.size.toString();
            
            // Count recent uploads (last 24 hours)
            const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
            const recentCount = files.filter(file => {
                if (file.upload_time) {
                    return new Date(file.upload_time) > oneDayAgo;
                }
                return false;
            }).length;
            document.getElementById('recentUploads').textContent = recentCount.toString();
            
            // Load notification statistics
            if (typeof loadNotificationStats === 'function') {
                loadNotificationStats();
            } else {
                document.getElementById('activeNotifications').textContent = '0';
            }
            
            // Load recent activity with real data
            loadRecentActivity(files);
        } else {
            // Fallback to default values
            document.getElementById('totalFiles').textContent = '0';
            document.getElementById('totalTags').textContent = '0';
            document.getElementById('recentUploads').textContent = '0';
            document.getElementById('activeNotifications').textContent = '0';
            document.getElementById('recentActivity').innerHTML = '<p class="text-muted">No recent activity</p>';
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        // Fallback to default values
        document.getElementById('totalFiles').textContent = '0';
        document.getElementById('totalTags').textContent = '0';
        document.getElementById('recentUploads').textContent = '0';
        document.getElementById('activeNotifications').textContent = '0';
        document.getElementById('recentActivity').innerHTML = '<p class="text-muted">Error loading recent activity</p>';
    }
}

function loadRecentActivity(files) {
    const recentActivityContainer = document.getElementById('recentActivity');
    if (!recentActivityContainer) return;
    
    // Clear existing content
    recentActivityContainer.innerHTML = '';
    
    if (!files || files.length === 0) {
        recentActivityContainer.innerHTML = '<p class="text-gray-500">No recent activity</p>';
        return;
    }
    
    // Sort files by upload time (most recent first)
    const sortedFiles = files.sort((a, b) => new Date(b.upload_time) - new Date(a.upload_time));
    
    // Show only the most recent 5 activities
    const recentFiles = sortedFiles.slice(0, 5);
    
    recentFiles.forEach(file => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item mb-3 p-3 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow';
        
        const timeAgo = getTimeAgo(file.upload_time);
        
        // Create status badge based on detection
        let statusBadge = '';
        if (file.detected_species && file.detected_species.length > 0) {
            const species = file.detected_species[0]; // Use first detected species
            const confidence = file.confidence ? ` (${(file.confidence * 100).toFixed(0)}%)` : '';
            statusBadge = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                ✓ ${species}${confidence}
            </span>`;
        } else {
            statusBadge = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                📄 Processing
            </span>`;
        }
        
        // Add other user tags if any
        let userTags = '';
        const otherTags = file.tags.filter(tag => 
            !file.detected_species.includes(tag) && tag !== 'uploaded'
        );
        if (otherTags.length > 0) {
            userTags = otherTags.map(tag => 
                `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-700">${tag}</span>`
            ).join(' ');
        }
        
        activityItem.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="text-sm font-medium text-gray-900">📤 File uploaded</span>
                        <span class="text-xs text-gray-500">${timeAgo}</span>
                    </div>
                    <div class="text-sm text-gray-600 mb-2 truncate" title="${file.filename}">
                        ${file.filename}
                    </div>
                    <div class="flex flex-wrap gap-1">
                        ${statusBadge}
                        ${userTags}
                    </div>
                </div>
            </div>
        `;
        
        recentActivityContainer.appendChild(activityItem);
    });
}

function getTimeAgo(uploadTime) {
    const now = new Date();
    const uploadDate = new Date(uploadTime);
    const diffInSeconds = Math.floor((now - uploadDate) / 1000);
    
    if (diffInSeconds < 60) {
        return `${diffInSeconds} seconds ago`;
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    }
}

// Auto-refresh dashboard every 30 seconds
setInterval(() => {
    if (document.getElementById('dashboard') && !document.getElementById('dashboard').classList.contains('d-none')) {
        loadDashboard();
    }
}, 30000); 