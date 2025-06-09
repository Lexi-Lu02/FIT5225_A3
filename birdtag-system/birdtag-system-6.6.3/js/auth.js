// Authentication Module
function checkAuth() {
    console.log('Checking authentication...');
    
    if (config.isLocalTesting) {
        return checkLocalAuth();
    }
    
    // AWS Cognito authentication check
    const idToken = localStorage.getItem('idToken');
    const accessToken = localStorage.getItem('accessToken');
    
    if (!idToken || !accessToken) {
        console.log('No Cognito tokens found, showing login modal');
        showLoginModal();
        return false;
    }
    
    try {
        // Decode ID token to check expiration
        const payload = JSON.parse(atob(idToken.split('.')[1]));
        const expiration = payload.exp * 1000;
        
        if (Date.now() > expiration) {
            console.log('Token expired, clearing storage');
            localStorage.clear();
            showLoginModal();
            return false;
        }
        
        currentUser = { 
            id: payload.sub, 
            email: payload.email,
            username: payload['cognito:username']
        };
        console.log('User authenticated:', currentUser);
        
        // Update UI with user info
        const userEmailElement = document.getElementById('userEmail');
        if (userEmailElement) {
            userEmailElement.textContent = payload.email || 'User';
        }
        
        return true;
    } catch (e) {
        console.error('Token validation error:', e);
        localStorage.clear();
        showLoginModal();
        return false;
    }
}

function checkLocalAuth() {
    const token = localStorage.getItem('authToken');
    
    if (!token) {
        console.log('No local token found, showing login modal');
        showLoginModal();
        return false;
    }
    
    try {
        // Decode token to check expiration
        const payload = JSON.parse(atob(token.split('.')[1]));
        const expiration = payload.exp * 1000;
        
        if (Date.now() > expiration) {
            console.log('Token expired, clearing storage');
            localStorage.clear();
            showLoginModal();
            return false;
        }
        
        currentUser = { id: payload.id, email: payload.email };
        console.log('User authenticated:', currentUser);
        
        // Update UI with user info
        const userEmailElement = document.getElementById('userEmail');
        if (userEmailElement) {
            userEmailElement.textContent = payload.email || 'User';
        }
        
        return true;
    } catch (e) {
        console.error('Token validation error:', e);
        localStorage.clear();
        showLoginModal();
        return false;
    }
}

function showLoginModal() {
    console.log('Attempting to show login modal...');
    // Wait for DOM to be ready
    setTimeout(() => {
        const modalElement = document.getElementById('loginModal');
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement, {
                backdrop: 'static',
                keyboard: false
            });
            modal.show();
            console.log('Login modal shown');
        } else {
            console.error('Login modal element not found');
        }
    }, 100);
}

function signOut() {
    localStorage.clear();
    currentUser = null;
    showToast('Logged out successfully', 'success');
    setTimeout(() => location.reload(), 1000);
}

// Login handler - supports both local testing and AWS Cognito
async function handleLogin(e) {
    e.preventDefault();
    console.log('Handling login...');
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    if (!email || !password) {
        showToast('Please fill in all fields', 'error');
        return;
    }
    
    if (config.isLocalTesting) {
        return handleLocalLogin(email, password);
    }
    
    // AWS Cognito login would be implemented here
    showToast('AWS Cognito login not implemented yet', 'warning');
}

async function handleLocalLogin(email, password) {
    try {
        showLoading(true);
        const response = await fetch(`${config.apiGatewayUrl}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        console.log('Login response:', data);
        
        if (response.ok) {
            localStorage.setItem('authToken', data.token);
            currentUser = data.user;
            showToast('Login successful!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('loginModal')).hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.message || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('Login error:', error);
        showToast('Login failed - server error', 'error');
    } finally {
        showLoading(false);
    }
}

// Signup handler - supports both local testing and AWS Cognito
async function handleSignup(e) {
    e.preventDefault();
    console.log('Handling signup...');
    
    const email = document.getElementById('signupEmail').value;
    const password = document.getElementById('signupPassword').value;
    
    if (!email || !password) {
        showToast('Please fill in all fields', 'error');
        return;
    }
    
    // Validate password (at least 8 characters, with uppercase, lowercase, and numbers)
    const passwordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$/;
    if (!passwordRegex.test(password)) {
        showToast('Password must be at least 8 characters with uppercase, lowercase, and numbers', 'error');
        return;
    }
    
    if (config.isLocalTesting) {
        return handleLocalSignup(email, password);
    }
    
    // AWS Cognito signup would be implemented here
    showToast('AWS Cognito signup not implemented yet', 'warning');
}

async function handleLocalSignup(email, password) {
    try {
        showLoading(true);
        const response = await fetch(`${config.apiGatewayUrl}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password, name: email.split('@')[0] })
        });
        
        const data = await response.json();
        console.log('Signup response:', data);
        
        if (response.ok) {
            localStorage.setItem('authToken', data.token);
            currentUser = data.user;
            showToast('Account created successfully!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('signupModal')).hide();
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.message || 'Signup failed', 'error');
        }
    } catch (error) {
        console.error('Signup error:', error);
        showToast('Signup failed - server error', 'error');
    } finally {
        showLoading(false);
    }
}

// Function to get current user
function getCurrentUser() {
    if (currentUser) {
        return currentUser;
    }
    
    // Try to get user from stored token
    if (config.isLocalTesting) {
        const token = localStorage.getItem('authToken');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                if (Date.now() < payload.exp * 1000) {
                    return { id: payload.id, email: payload.email };
                }
            } catch (e) {
                console.error('Error parsing stored token:', e);
            }
        }
    } else {
        const idToken = localStorage.getItem('idToken');
        if (idToken) {
            try {
                const payload = JSON.parse(atob(idToken.split('.')[1]));
                if (Date.now() < payload.exp * 1000) {
                    return { 
                        id: payload.sub, 
                        email: payload.email,
                        username: payload['cognito:username']
                    };
                }
            } catch (e) {
                console.error('Error parsing stored token:', e);
            }
        }
    }
    
    return null;
} 