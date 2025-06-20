// Navigation Module
function showPage(pageName) {
    document.querySelectorAll('.page').forEach(page => {
        page.style.display = 'none';
    });
    
    document.getElementById(pageName + 'Page').style.display = 'block';
    
    // Update active nav link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Load page-specific data
    if (pageName === 'dashboard') loadDashboard();
    if (pageName === 'myfiles') loadMyFiles();
    if (pageName === 'notifications') loadSubscriptions();
} 