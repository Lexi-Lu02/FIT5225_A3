// BirdTag Configuration
const config = {
    region: 'us-east-1',
    userPoolId: 'YOUR_USER_POOL_ID',
    clientId: 'YOUR_CLIENT_ID',
    apiGatewayUrl: 'YOUR_API_GATEWAY_URL'
};

// Global variables
let currentUser = null;
let selectedFiles = new Set();
let currentFileUrl = null; 