// Main Application Module
// Initialize on page load
window.onload = function() {
    console.log('BirdTag application initializing...');
    
    // show current configuration mode
    if (config.isLocalTesting) {
        console.log('Running in Local Testing Mode');
        showToast('Local Testing Mode', 'info');
    } else if (config.isLambdaTesting) {
        console.log('Running in Lambda Testing Mode');
        showToast('Lambda Testing Mode - Please configure AWS credentials', 'info');
    } else {
        console.log('Running in Production Mode');
    }
    
    // Initialize in sequence
    setupEventListeners();
    loadTheme();
    setupDropZone();
    
    // Check authentication after DOM is ready
    setTimeout(() => {
        const isAuthenticated = checkAuth();
        console.log('Authentication status:', isAuthenticated);
        
        // Load initial data if user is authenticated
        if (isAuthenticated) {
            loadMediaFiles();
        }
        
        // Initialize search functionality
        setupSearch();
    }, 100);
};

function setupEventListeners() {
    console.log('Setting up event listeners...');
    
    // Login form
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
        console.log('Login form listener added');
    }
    
    // Signup form
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
        console.log('Signup form listener added');
    }
    
    // Subscription form (placeholder)
    const subscriptionForm = document.getElementById('subscriptionForm');
    if (subscriptionForm) {
        subscriptionForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await subscribe(e);
        });
    }
    
    // Theme toggle
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // Sign out button
    const signOutBtn = document.getElementById('signOutBtn');
    if (signOutBtn) {
        signOutBtn.addEventListener('click', signOut);
    }
    
    // Profile button
    const profileBtn = document.getElementById('profileBtn');
    if (profileBtn) {
        profileBtn.addEventListener('click', showProfile);
    }
}

function showLoading(show) {
    // Try to find loading overlay
    let loadingOverlay = document.querySelector('.loading-overlay');
    
    // If it doesn't exist, create it
    if (!loadingOverlay) {
        loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.7);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
        `;
        loadingOverlay.innerHTML = `
            <div style="background: white; padding: 20px; border-radius: 10px; text-align: center;">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <div style="margin-top: 10px;">Loading...</div>
            </div>
        `;
        document.body.appendChild(loadingOverlay);
    }
    
    loadingOverlay.style.display = show ? 'flex' : 'none';
    console.log('Loading overlay:', show ? 'shown' : 'hidden');
}

// Profile functionality
function showProfile() {
    if (!currentUser) {
        showToast('Please login first', 'error');
        return;
    }
    
    showToast(`User Profile: ${currentUser.email}`, 'info');
}

// Subscription functionality (placeholder)
async function subscribe(e) {
    e.preventDefault();
    showToast('Subscription functionality coming soon', 'info');
}

// Dashboard functionality
function updateDashboard() {
    const token = localStorage.getItem('authToken');
    if (!token) return;
    
    // Update user stats, recent uploads, etc.
    loadMediaFiles();
}

// Initialize tooltips and other Bootstrap components
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}); 