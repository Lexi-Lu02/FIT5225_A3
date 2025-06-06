// Main Application Module
// Initialize on page load
window.onload = function() {
    checkAuth();
    setupDropZone();
    setupEventListeners();
    loadTheme();
};

function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleLogin(e);
    });
    
    // Signup form
    document.getElementById('signupForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleSignup(e);
    });
    
    // Subscription form
    document.getElementById('subscriptionForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        await subscribe(e);
    });
}

function showLoading(show) {
    document.querySelector('.loading-overlay').style.display = show ? 'flex' : 'none';
}

// Profile
function showProfile() {
    showToast('Profile page coming soon', 'info');
} 