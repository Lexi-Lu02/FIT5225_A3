import os
import time
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.error_utils import BirdTagError, ErrorCode
from utils.dynamo_utils import create_model_metric, get_model_metrics

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables with defaults
MODEL_METRICS_TABLE = os.environ.get('MODEL_METRICS_TABLE', 'BirdTagModelMetrics')
MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
MODEL_KEY = os.environ.get('MODEL_KEY', 'model.pt')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '10485760'))  # 10MB default

def check_required_env_vars() -> None:
    """
    Check if all required environment variables are set
    
    Raises:
        BirdTagError: If any required environment variable is missing
    """
    missing_vars = []
    
    if not MODEL_BUCKET:
        missing_vars.append('MODEL_BUCKET')
    
    if missing_vars:
        raise BirdTagError(
            message="Missing required environment variables",
            error_code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500,
            details={"missing_variables": missing_vars}
        )

class ModelMetrics:
    """Class to track model performance metrics"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.start_time = time.time()
        self.metrics = {
            'modelName': model_name,
            'timestamp': datetime.utcnow().isoformat(),
            'processingTime': 0,
            'inputSize': 0,
            'outputSize': 0,
            'success': False,
            'error': None,
            'confidence': 0,
            'detections': 0
        }
    
    def set_input_size(self, size: int) -> None:
        """Set input size in bytes"""
        self.metrics['inputSize'] = size
    
    def set_output_size(self, size: int) -> None:
        """Set output size in bytes"""
        self.metrics['outputSize'] = size
    
    def set_confidence(self, confidence: float) -> None:
        """Set model confidence score"""
        self.metrics['confidence'] = confidence
    
    def set_detections(self, count: int) -> None:
        """Set number of detections"""
        self.metrics['detections'] = count
    
    def set_error(self, error: str) -> None:
        """Set error message"""
        self.metrics['error'] = error
        self.metrics['success'] = False
    
    def complete(self) -> Dict[str, Any]:
        """Complete metrics collection and save to database"""
        try:
            # Calculate processing time
            self.metrics['processingTime'] = time.time() - self.start_time
            
            # Set success if no error
            if not self.metrics['error']:
                self.metrics['success'] = True
            
            # Save metrics to database
            if MODEL_METRICS_TABLE:
                create_model_metric(self.metrics)
            
            return self.metrics
            
        except Exception as e:
            logger.error(f"Failed to save model metrics: {str(e)}")
            return self.metrics

def get_model_performance(
    model_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Get model performance metrics
    
    Args:
        model_name (str): Name of the model
        start_date (Optional[str]): Start date for metrics (ISO format)
        end_date (Optional[str]): End date for metrics (ISO format)
        limit (int): Maximum number of metrics to return
        
    Returns:
        Dict[str, Any]: Model performance metrics
        
    Raises:
        BirdTagError: If metrics retrieval fails
    """
    try:
        if not MODEL_METRICS_TABLE:
            raise BirdTagError(
                message="Model metrics table not configured",
                error_code=ErrorCode.CONFIGURATION_ERROR,
                status_code=500
            )
        
        # Get metrics from database
        metrics = get_model_metrics(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        # Calculate performance statistics
        total_runs = len(metrics['items'])
        successful_runs = sum(1 for m in metrics['items'] if m.get('success', False))
        total_processing_time = sum(m.get('processingTime', 0) for m in metrics['items'])
        total_detections = sum(m.get('detections', 0) for m in metrics['items'])
        
        return {
            'modelName': model_name,
            'totalRuns': total_runs,
            'successfulRuns': successful_runs,
            'successRate': (successful_runs / total_runs * 100) if total_runs > 0 else 0,
            'averageProcessingTime': (total_processing_time / total_runs) if total_runs > 0 else 0,
            'totalDetections': total_detections,
            'averageDetections': (total_detections / total_runs) if total_runs > 0 else 0,
            'metrics': metrics['items']
        }
        
    except Exception as e:
        logger.error(f"Failed to get model performance: {str(e)}")
        raise BirdTagError(
            message="Failed to get model performance",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def validate_model_input(
    file_path: str,
    file_type: str,
    max_size: Optional[int] = None
) -> None:
    """
    Validate model input file
    
    Args:
        file_path (str): Path to input file
        file_type (str): Type of file (image/audio)
        max_size (int, optional): Maximum file size in bytes
        
    Raises:
        BirdTagError: If validation fails
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise BirdTagError(
                message="Input file not found",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Check file size
        file_size = os.path.getsize(file_path)
        max_allowed_size = max_size or MAX_FILE_SIZE
        if file_size > max_allowed_size:
            raise BirdTagError(
                message=f"File size exceeds maximum limit of {max_allowed_size/1024/1024}MB",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Validate file type
        if file_type == 'image':
            if not file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise BirdTagError(
                    message="Invalid image format. Supported formats: JPG, JPEG, PNG",
                    error_code=ErrorCode.INVALID_INPUT,
                    status_code=400
                )
        elif file_type == 'audio':
            if not file_path.lower().endswith(('.wav', '.mp3')):
                raise BirdTagError(
                    message="Invalid audio format. Supported formats: WAV, MP3",
                    error_code=ErrorCode.INVALID_INPUT,
                    status_code=400
                )
        else:
            raise BirdTagError(
                message="Invalid file type",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to validate model input: {str(e)}")
        raise BirdTagError(
            message="Failed to validate model input",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_model_status(model_name: str) -> Dict[str, Any]:
    """
    Get current model status
    
    Args:
        model_name (str): Name of the model
        
    Returns:
        Dict[str, Any]: Model status information
        
    Raises:
        BirdTagError: If status retrieval fails
    """
    try:
        # Check required environment variables
        check_required_env_vars()
        
        # Get recent metrics
        metrics = get_model_metrics(
            model_name=model_name,
            limit=1
        )
        
        if not metrics['items']:
            return {
                'modelName': model_name,
                'status': 'unknown',
                'lastRun': None,
                'lastSuccess': None,
                'lastError': None
            }
        
        latest = metrics['items'][0]
        
        return {
            'modelName': model_name,
            'status': 'active' if latest.get('success', False) else 'error',
            'lastRun': latest.get('timestamp'),
            'lastSuccess': latest.get('success', False),
            'lastError': latest.get('error'),
            'lastProcessingTime': latest.get('processingTime'),
            'lastDetections': latest.get('detections')
        }
        
    except Exception as e:
        logger.error(f"Failed to get model status: {str(e)}")
        raise BirdTagError(
            message="Failed to get model status",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 