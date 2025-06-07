import os
import logging
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional, Union

from utils.error_utils import BirdTagError, ErrorCode

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def load_audio_file(file_path: str, target_sr: int = 48000) -> Tuple[np.ndarray, int]:
    """
    Load audio file and convert to target sample rate
    
    Args:
        file_path (str): Path to audio file
        target_sr (int): Target sample rate
    
    Returns:
        Tuple[np.ndarray, int]: Audio data and sample rate
        
    Raises:
        BirdTagError: If audio loading fails
    """
    try:
        if not os.path.exists(file_path):
            raise BirdTagError(
                message="Audio file not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        # Load audio file
        audio_data, sr = librosa.load(file_path, sr=target_sr)
        if audio_data is None or len(audio_data) == 0:
            raise BirdTagError(
                message="Failed to load audio data",
                error_code=ErrorCode.FILE_PROCESSING_ERROR,
                status_code=400
            )
        return audio_data, sr
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error loading audio file: {str(e)}")
        raise BirdTagError(
            message="Failed to load audio file",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def convert_to_wav(input_path: str, output_path: str, target_sr: int = 48000) -> str:
    """
    Convert audio file to WAV format
    
    Args:
        input_path (str): Path to input audio file
        output_path (str): Path to save WAV file
        target_sr (int): Target sample rate
    
    Returns:
        str: Path to converted WAV file
        
    Raises:
        BirdTagError: If conversion fails
    """
    try:
        if not os.path.exists(input_path):
            raise BirdTagError(
                message="Input audio file not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        # Load audio file
        audio_data, sr = load_audio_file(input_path, target_sr)
        
        # Save as WAV
        sf.write(output_path, audio_data, target_sr)
        
        return output_path
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error converting to WAV: {str(e)}")
        raise BirdTagError(
            message="Failed to convert audio to WAV",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def extract_audio_segment(
    audio_data: np.ndarray,
    sr: int,
    start_time: float,
    duration: float
) -> np.ndarray:
    """
    Extract segment from audio data
    
    Args:
        audio_data (np.ndarray): Audio data
        sr (int): Sample rate
        start_time (float): Start time in seconds
        duration (float): Duration in seconds
    
    Returns:
        np.ndarray: Extracted audio segment
        
    Raises:
        BirdTagError: If segment extraction fails
    """
    try:
        if audio_data is None or len(audio_data) == 0:
            raise BirdTagError(
                message="Invalid audio data",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        if start_time < 0 or duration <= 0:
            raise BirdTagError(
                message="Invalid time parameters",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        start_sample = int(start_time * sr)
        end_sample = int((start_time + duration) * sr)
        
        if start_sample >= len(audio_data) or end_sample > len(audio_data):
            raise BirdTagError(
                message="Time parameters out of range",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        return audio_data[start_sample:end_sample]
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error extracting audio segment: {str(e)}")
        raise BirdTagError(
            message="Failed to extract audio segment",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def normalize_audio(audio_data: np.ndarray) -> np.ndarray:
    """
    Normalize audio data to [-1, 1] range
    
    Args:
        audio_data (np.ndarray): Audio data
    
    Returns:
        np.ndarray: Normalized audio data
        
    Raises:
        BirdTagError: If normalization fails
    """
    try:
        if audio_data is None or len(audio_data) == 0:
            raise BirdTagError(
                message="Invalid audio data",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        return librosa.util.normalize(audio_data)
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error normalizing audio: {str(e)}")
        raise BirdTagError(
            message="Failed to normalize audio",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_audio_duration(file_path: str) -> float:
    """
    Get duration of audio file in seconds
    
    Args:
        file_path (str): Path to audio file
    
    Returns:
        float: Duration in seconds
        
    Raises:
        BirdTagError: If getting duration fails
    """
    try:
        if not os.path.exists(file_path):
            raise BirdTagError(
                message="Audio file not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        duration = librosa.get_duration(path=file_path)
        if duration <= 0:
            raise BirdTagError(
                message="Invalid audio duration",
                error_code=ErrorCode.FILE_PROCESSING_ERROR,
                status_code=400
            )
        return duration
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        raise BirdTagError(
            message="Failed to get audio duration",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def is_valid_audio_file(file_path: str) -> bool:
    """
    Check if file is a valid audio file
    
    Args:
        file_path (str): Path to audio file
    
    Returns:
        bool: True if valid audio file
    """
    try:
        if not os.path.exists(file_path):
            return False
            
        # Try to load the file
        librosa.load(file_path, sr=None, duration=0.1)
        return True
    except Exception:
        return False 