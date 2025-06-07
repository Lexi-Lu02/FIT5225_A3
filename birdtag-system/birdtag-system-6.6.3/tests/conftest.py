import os
import sys
import pytest
import boto3
from unittest.mock import patch, MagicMock
from moto import mock_dynamodb, mock_s3

# 设置环境变量
os.environ['PYTHONPATH'] = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.environ['PYTHONNOUSERSITE'] = '1'
os.environ['MPLBACKEND'] = 'Agg'

# 设置测试环境变量
os.environ['COGNITO_CLIENT_ID'] = 'test-client-id'
os.environ['COGNITO_USER_POOL_ID'] = 'test-user-pool'
os.environ['JWT_SECRET'] = 'test-jwt-secret'
os.environ['IS_LOCAL'] = 'true'
os.environ['USERS_TABLE'] = 'BirdTagUsers'
os.environ['DYNAMODB_TABLE'] = 'BirdTagMedia'

# 修改 sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path = [p for p in sys.path if 'layers' not in p]
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# 创建一个空的 matplotlib 配置目录
matplotlib_config_dir = os.path.join(os.path.dirname(__file__), '.matplotlib')
os.makedirs(matplotlib_config_dir, exist_ok=True)
os.environ['MPLCONFIGDIR'] = matplotlib_config_dir

# 创建一个空的 matplotlib 测试数据目录
matplotlib_test_data_dir = os.path.join(matplotlib_config_dir, 'test_data')
os.makedirs(matplotlib_test_data_dir, exist_ok=True)

# 创建一个空的 baseline 目录
baseline_dir = os.path.join(matplotlib_test_data_dir, 'baseline')
os.makedirs(baseline_dir, exist_ok=True)

def pytest_configure(config):
    """Configure pytest based on Python version"""
    python_version = sys.version_info
    if python_version.major != 3:
        pytest.exit("Python 3 is required")
    
    # 检查 Python 版本兼容性
    if python_version.minor < 9:
        pytest.exit("Python 3.9 or higher is required")
    
    # 设置环境变量
    os.environ["PYTHON_VERSION"] = f"{python_version.major}.{python_version.minor}"

# Mock AWS services
@pytest.fixture(autouse=True)
def mock_aws_services():
    """Mock AWS services for all tests"""
    with patch('boto3.client') as mock_client:
        # Mock Cognito client
        mock_cognito = MagicMock()
        mock_client.return_value = mock_cognito
        yield mock_cognito

# Mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    """Set up test environment variables"""
    with patch.dict(os.environ, {
        'USER_POOL_ID': 'test-user-pool',
        'CLIENT_ID': 'test-client-id',
        'IS_LOCAL': 'true'
    }):
        yield

# Mock DynamoDB
@pytest.fixture
def mock_dynamodb():
    """Mock DynamoDB for testing"""
    with patch('boto3.resource') as mock_resource:
        mock_table = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        yield mock_table

# Mock S3
@pytest.fixture
def mock_s3():
    """Mock S3 for testing"""
    with patch('boto3.client') as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        yield mock_s3

# Mock Rekognition
@pytest.fixture
def mock_rekognition():
    """Mock Rekognition for testing"""
    with patch('boto3.client') as mock_client:
        mock_rekognition = MagicMock()
        mock_client.return_value = mock_rekognition
        yield mock_rekognition

# Mock CloudWatch
@pytest.fixture
def mock_cloudwatch():
    """Mock CloudWatch for testing"""
    with patch('boto3.client') as mock_client:
        mock_cloudwatch = MagicMock()
        mock_client.return_value = mock_cloudwatch
        yield mock_cloudwatch

@pytest.fixture(scope="function")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["IS_LOCAL"] = "true"
    os.environ["JWT_SECRET"] = "local-test-secret"

@pytest.fixture(scope="function")
def dynamodb(aws_credentials):
    with mock_dynamodb():
        yield boto3.resource("dynamodb")

@pytest.fixture(scope="function")
def s3(aws_credentials):
    with mock_s3():
        yield boto3.client("s3")

@pytest.fixture(scope="function")
def cognito(aws_credentials):
    """Mock Cognito using unittest.mock"""
    with patch('boto3.client') as mock_client:
        mock_cognito = mock_client.return_value
        # 设置模拟的 Cognito 响应
        mock_cognito.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token',
                'IdToken': 'mock-id-token',
                'RefreshToken': 'mock-refresh-token'
            }
        }
        mock_cognito.sign_up.return_value = {
            'UserConfirmed': False,
            'UserSub': 'mock-user-sub'
        }
        mock_cognito.confirm_sign_up.return_value = {}
        yield mock_cognito

@pytest.fixture(scope="function")
def local_mode():
    """Enable local mode for testing"""
    os.environ["IS_LOCAL"] = "true"
    yield
    os.environ.pop("IS_LOCAL", None)

@pytest.fixture(scope="function")
def python_version():
    """Get current Python version"""
    return f"{sys.version_info.major}.{sys.version_info.minor}" 
