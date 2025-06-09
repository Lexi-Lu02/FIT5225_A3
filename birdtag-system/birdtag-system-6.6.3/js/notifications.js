// Notifications Module

// 加载用户订阅信息
async function loadSubscriptions() {
    try {
        const user = getCurrentUser();
        if (!user || !user.email) {
            document.getElementById('subscriptionsList').innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> Please login to view your subscriptions
                </div>
            `;
            
            // Disable subscription form
            const emailInput = document.getElementById('subscriptionEmail');
            const speciesSelect = document.getElementById('subscriptionSpecies');
            const subscribeButton = document.querySelector('#subscriptionForm button[type="submit"]');
            
            if (emailInput) emailInput.disabled = true;
            if (speciesSelect) speciesSelect.disabled = true;
            if (subscribeButton) subscribeButton.disabled = true;
            
            return;
        }

        // Enable subscription form
        const emailInput = document.getElementById('subscriptionEmail');
        const speciesSelect = document.getElementById('subscriptionSpecies');
        const subscribeButton = document.querySelector('#subscriptionForm button[type="submit"]');
        
        if (emailInput) {
            emailInput.disabled = false;
            emailInput.value = user.email; // Pre-fill with user's email
        }
        if (speciesSelect) speciesSelect.disabled = false;
        if (subscribeButton) subscribeButton.disabled = false;

        const response = await fetch(`/api/v1/subscriptions?email=${encodeURIComponent(user.email)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Subscriptions loaded:', data);
        
        const container = document.getElementById('subscriptionsList');
        if (!container) return;
        
        if (!data.subscriptions || data.subscriptions.length === 0) {
            container.innerHTML = `
                <div class="alert alert-secondary">
                    <i class="bi bi-inbox"></i> No active subscriptions yet. Subscribe to bird species above to get notifications!
                </div>
            `;
            return;
        }
        
        // Handle both array of strings and array of objects
        const subscriptions = data.subscriptions.map(sub => {
            if (typeof sub === 'string') {
                return { species: sub, created_at: new Date().toISOString() };
            }
            return sub;
        });
        
        container.innerHTML = subscriptions.map(sub => `
            <div class="card mb-2">
                <div class="card-body d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-1">${sub.species}</h6>
                        <small class="text-muted">Subscribed on ${new Date(sub.created_at).toLocaleDateString()}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="unsubscribe('${sub.species}')">
                        <i class="bi bi-trash"></i> Unsubscribe
                    </button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading subscriptions:', error);
        document.getElementById('subscriptionsList').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> Failed to load subscriptions: ${error.message}
            </div>
        `;
    }
}

// 订阅通知
async function subscribe(event) {
    event.preventDefault();
    
    try {
        const user = getCurrentUser();
        if (!user || !user.email) {
            showToast('Please login to subscribe to notifications', 'warning');
            return;
        }
        
        const email = document.getElementById('subscriptionEmail').value;
        const species = document.getElementById('subscriptionSpecies').value;
        
        if (!email || !species) {
            showToast('Please fill in all fields', 'warning');
            return;
        }
        
        // Validate email format
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            showToast('Please enter a valid email address', 'error');
            return;
        }
        
        // Show loading state
        const submitButton = event.target.querySelector('button[type="submit"]');
        const originalText = submitButton.innerHTML;
        submitButton.innerHTML = '<i class="bi bi-hourglass-split"></i> Subscribing...';
        submitButton.disabled = true;
        
        const response = await fetch('/api/v1/subscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, species })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Successfully subscribed to ${species} notifications!`, 'success');
            
            // Clear form
            document.getElementById('subscriptionSpecies').value = '';
            
            // Reload subscriptions list
            loadSubscriptions();
            loadNotificationStats();
        } else {
            showToast(data.message || 'Subscription failed', 'error');
        }
        
        // Restore button state
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
        
    } catch (error) {
        console.error('Subscribe error:', error);
        showToast('Subscription failed - server error', 'error');
        
        // Restore button state
        const submitButton = event.target.querySelector('button[type="submit"]');
        if (submitButton) {
            submitButton.innerHTML = '<i class="bi bi-bell-fill"></i> Subscribe';
            submitButton.disabled = false;
        }
    }
}

// 取消订阅
async function unsubscribe(species) {
    try {
        const user = getCurrentUser();
        if (!user || !user.email) {
            showToast('Please login to manage subscriptions', 'warning');
            return;
        }
        
        if (!confirm(`Are you sure you want to unsubscribe from ${species} notifications?`)) {
            return;
        }
        
        const response = await fetch('/api/v1/unsubscribe', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email: user.email, 
                species: species 
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(`Successfully unsubscribed from ${species} notifications`, 'success');
            
            // Reload subscriptions list and stats
            loadSubscriptions();
            loadNotificationStats();
        } else {
            showToast(data.message || 'Unsubscribe failed', 'error');
        }
        
    } catch (error) {
        console.error('Unsubscribe error:', error);
        showToast('Unsubscribe failed - server error', 'error');
    }
}

// 加载通知历史
async function loadNotificationHistory() {
    try {
        const user = getCurrentUser();
        if (!user || !user.email) {
            document.getElementById('notificationHistory').innerHTML = `
                <div class="alert alert-info">
                    <i class="bi bi-info-circle"></i> Please login to view your notification history
                </div>
            `;
            return;
        }

        const response = await fetch(`/api/v1/notifications/history?email=${encodeURIComponent(user.email)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Notification history loaded:', data);
        
        const container = document.getElementById('notificationHistory');
        if (!container) return;
        
        if (!data.notifications || data.notifications.length === 0) {
            container.innerHTML = `
                <div class="alert alert-secondary">
                    <i class="bi bi-clock-history"></i> No notification history yet. Subscribe to bird species to start receiving notifications!
                </div>
            `;
            return;
        }
        
        container.innerHTML = data.notifications.map(notification => {
            const date = new Date(notification.timestamp);
            const timeAgo = getTimeAgo(notification.timestamp);
            
            return `
                <div class="card mb-3">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <div>
                            <i class="bi bi-bell-fill text-primary me-2"></i>
                            <strong>Bird Detection Alert</strong>
                        </div>
                        <small class="text-muted">${timeAgo}</small>
                    </div>
                    <div class="card-body">
                        <h6 class="card-title">${notification.species} detected!</h6>
                        <p class="card-text">
                            <strong>File:</strong> ${notification.filename}<br>
                            <strong>Confidence:</strong> ${(notification.detection_result.confidence * 100).toFixed(1)}%<br>
                            <strong>Detection ID:</strong> ${notification.id.substring(0, 8)}...
                        </p>
                        <div class="d-flex justify-content-between align-items-center">
                            <small class="text-muted">
                                Sent to: ${notification.email}
                            </small>
                            <span class="badge bg-success">
                                <i class="bi bi-check-circle"></i> ${notification.status}
                            </span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
    } catch (error) {
        console.error('Error loading notification history:', error);
        document.getElementById('notificationHistory').innerHTML = `
            <div class="alert alert-danger">
                <i class="bi bi-exclamation-triangle"></i> Failed to load notification history: ${error.message}
            </div>
        `;
    }
}

// 获取通知统计
async function loadNotificationStats() {
    try {
        const user = getCurrentUser();
        if (!user || !user.email) {
            // Set default stats when not logged in
            const activeNotificationsElement = document.getElementById('activeNotifications');
            if (activeNotificationsElement) {
                activeNotificationsElement.textContent = '0';
            }
            return;
        }

        const response = await fetch('/api/v1/notifications/stats', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Notification stats loaded:', data);
        
        // Update dashboard statistics
        const activeNotificationsElement = document.getElementById('activeNotifications');
        if (activeNotificationsElement) {
            activeNotificationsElement.textContent = data.stats?.total_subscriptions || '0';
        }
        
        // Update other statistics if elements exist
        const totalNotificationsElement = document.getElementById('totalNotifications');
        if (totalNotificationsElement) {
            totalNotificationsElement.textContent = data.stats?.total_notifications_sent || '0';
        }
        
        const todayNotificationsElement = document.getElementById('todayNotifications');
        if (todayNotificationsElement) {
            todayNotificationsElement.textContent = data.stats?.recent_notifications || '0';
        }
        
    } catch (error) {
        console.error('Error loading notification stats:', error);
        // Set fallback values
        const activeNotificationsElement = document.getElementById('activeNotifications');
        if (activeNotificationsElement) {
            activeNotificationsElement.textContent = '0';
        }
    }
}

// Helper function to format time ago
function getTimeAgo(timestamp) {
    const now = new Date();
    const past = new Date(timestamp);
    const diffInSeconds = Math.floor((now - past) / 1000);
    
    if (diffInSeconds < 60) {
        return 'just now';
    } else if (diffInSeconds < 3600) {
        const minutes = Math.floor(diffInSeconds / 60);
        return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 86400) {
        const hours = Math.floor(diffInSeconds / 3600);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else if (diffInSeconds < 604800) {
        const days = Math.floor(diffInSeconds / 86400);
        return `${days} day${days > 1 ? 's' : ''} ago`;
    } else {
        return past.toLocaleDateString();
    }
}

// 页面加载时初始化通知系统
document.addEventListener('DOMContentLoaded', function() {
    // 如果当前页面包含通知表单，添加事件监听器
    const subscriptionForm = document.getElementById('subscriptionForm');
    if (subscriptionForm) {
        subscriptionForm.addEventListener('submit', subscribe);
        
        // 自动填充当前用户的邮箱
        const user = getCurrentUser();
        const emailInput = document.getElementById('notificationEmail');
        if (user && user.email && emailInput) {
            emailInput.value = user.email;
        }
    }
    
    // 加载初始数据
    if (typeof loadSubscriptions === 'function') {
        loadSubscriptions();
    }
    
    if (typeof loadNotificationHistory === 'function') {
        loadNotificationHistory();
    }
    
    if (typeof loadNotificationStats === 'function') {
        loadNotificationStats();
    }
});

// 刷新所有通知相关数据
function refreshNotifications() {
    console.log('Refreshing all notification data...');
    loadSubscriptions();
    loadNotificationHistory();
    loadNotificationStats();
} 