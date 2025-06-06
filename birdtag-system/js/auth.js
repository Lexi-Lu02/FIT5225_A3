// Authentication Module
function checkAuth() {
    const idToken = localStorage.getItem('idToken');
    if (!idToken) {
        showLoginModal();
        return false;
    }
    
    try {
        // Decode token to check expiration
        const payload = JSON.parse(atob(idToken.split('.')[1]));
        const expiration = payload.exp * 1000;
        
        if (Date.now() > expiration) {
            localStorage.clear();
            showLoginModal();
            return false;
        }
        
        document.getElementById('userEmail').textContent = payload.email || 'User';
        return true;
    } catch (e) {
        localStorage.clear();
        showLoginModal();
        return false;
    }
}

function showLoginModal() {
    const modal = new bootstrap.Modal(document.getElementById('loginModal'));
    modal.show();
}

function signOut() {
    localStorage.clear();
    showToast('Logged out successfully', 'success');
    setTimeout(() => location.reload(), 1000);
}

// Login and Signup handlers will be set up in setupEventListeners
async function handleLogin(e) {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    // Simulate login - in real app, call Cognito
    showToast('Login functionality needs Cognito integration', 'info');
    
    // For demo, store fake token
    const fakeToken = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTl9.fake';
    localStorage.setItem('idToken', fakeToken);
    
    bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
    location.reload();
}

async function handleSignup(e) {
    e.preventDefault();
    showToast('Signup functionality needs Cognito integration', 'info');
} 