// BirdTag Configuration - 本地测试模式
const config = {
    // 本地测试模式
    isLocalTesting: true,
    isLambdaTesting: false,
    isProduction: false,
    
    // 本地服务器配置
    localApiUrl: 'http://localhost:8080/api',
    
    // AWS配置 (本地测试时不使用)
    region: 'us-east-1',
    userPoolId: 'local-test-pool',
    clientId: 'local-test-client',
    apiGatewayUrl: 'http://localhost:8080/api'
};

// Global variables
let currentUser = null;
let selectedFiles = new Set();
let currentFileUrl = null; 