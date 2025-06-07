// Notifications Module
async function loadSubscriptions() {
    if (!checkAuth()) return;
    
    // This would load existing subscriptions
    // For now, show placeholder
    document.getElementById('subscriptionsList').innerHTML = `
        <div class="list-group">
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <i class="bi bi-bell me-2"></i>
                        <span>Crow notifications</span>
                    </div>
                    <button class="btn btn-sm btn-outline-danger" onclick="unsubscribe('crow')">
                        <i class="bi bi-bell-slash"></i> Unsubscribe
                    </button>
                </div>
            </div>
        </div>
    `;
}

async function subscribe(event) {
    if (event) event.preventDefault();
    if (!checkAuth()) return;
    
    const email = document.getElementById('notificationEmail').value;
    const species = document.getElementById('notificationSpecies').value;
    
    if (!email || !species) {
        showToast('Please fill all fields', 'warning');
        return;
    }
    
    showLoading(true);
    
    try {
        const response = await fetch(`${config.apiGatewayUrl}/v1/subscribe`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, species })
        });
        
        if (!response.ok) throw new Error('Subscription failed');
        
        showToast('Subscribed successfully!', 'success');
        document.getElementById('subscriptionForm').reset();
        loadSubscriptions();
        
    } catch (error) {
        console.error('Subscribe error:', error);
        showToast('Failed to subscribe: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
}

async function unsubscribe(species) {
    if (!checkAuth()) return;
    
    showLoading(true);
    
    try {
        const response = await fetch(`${config.apiGatewayUrl}/v1/unsubscribe`, {
            method: 'POST',
            headers: {
                'Authorization': localStorage.getItem('idToken'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ 
                email: document.getElementById('userEmail').textContent,
                species 
            })
        });
        
        if (!response.ok) throw new Error('Unsubscribe failed');
        
        showToast('Unsubscribed successfully!', 'success');
        loadSubscriptions();
        
    } catch (error) {
        console.error('Unsubscribe error:', error);
        showToast('Failed to unsubscribe: ' + error.message, 'danger');
    } finally {
        showLoading(false);
    }
} 