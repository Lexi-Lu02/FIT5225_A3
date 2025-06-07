import os
import logging
import numpy as np
from PIL import Image
from typing import Tuple, Optional, Union
import cv2

from utils.error_utils import BirdTagError, ErrorCode

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def load_image(file_path: str) -> np.ndarray:
    """
    Load image file as numpy array
    
    Args:
        file_path (str): Path to image file
    
    Returns:
        np.ndarray: Image data
        
    Raises:
        BirdTagError: If image loading fails
    """
    try:
        if not os.path.exists(file_path):
            raise BirdTagError(
                message="Image file not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        image = cv2.imread(file_path)
        if image is None:
            raise BirdTagError(
                message="Failed to load image",
                error_code=ErrorCode.FILE_PROCESSING_ERROR,
                status_code=400
            )
        return image
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error loading image: {str(e)}")
        raise BirdTagError(
            message="Failed to load image",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def resize_image(
    image: np.ndarray,
    target_size: Tuple[int, int],
    keep_aspect_ratio: bool = True
) -> np.ndarray:
    """
    Resize image to target size
    
    Args:
        image (np.ndarray): Image data
        target_size (Tuple[int, int]): Target size (width, height)
        keep_aspect_ratio (bool): Whether to keep aspect ratio
    
    Returns:
        np.ndarray: Resized image
        
    Raises:
        BirdTagError: If resizing fails
    """
    try:
        if image is None or image.size == 0:
            raise BirdTagError(
                message="Invalid image data",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        if keep_aspect_ratio:
            h, w = image.shape[:2]
            aspect = w / h
            if aspect > 1:
                new_w = target_size[0]
                new_h = int(new_w / aspect)
            else:
                new_h = target_size[1]
                new_w = int(new_h * aspect)
            return cv2.resize(image, (new_w, new_h))
        else:
            return cv2.resize(image, target_size)
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}")
        raise BirdTagError(
            message="Failed to resize image",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def convert_to_jpg(input_path: str, output_path: str, quality: int = 95) -> str:
    """
    Convert image to JPG format
    
    Args:
        input_path (str): Path to input image
        output_path (str): Path to save JPG file
        quality (int): JPEG quality (0-100)
    
    Returns:
        str: Path to converted JPG file
        
    Raises:
        BirdTagError: If conversion fails
    """
    try:
        if not os.path.exists(input_path):
            raise BirdTagError(
                message="Input image not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        image = Image.open(input_path)
        if image.mode in ('RGBA', 'LA'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[-1])
            image = background
        image.convert('RGB').save(output_path, 'JPEG', quality=quality)
        return output_path
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error converting to JPG: {str(e)}")
        raise BirdTagError(
            message="Failed to convert image to JPG",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def normalize_image(image: np.ndarray) -> np.ndarray:
    """
    Normalize image to [0, 1] range
    
    Args:
        image (np.ndarray): Image data
    
    Returns:
        np.ndarray: Normalized image
        
    Raises:
        BirdTagError: If normalization fails
    """
    try:
        if image is None or image.size == 0:
            raise BirdTagError(
                message="Invalid image data",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        return image.astype(np.float32) / 255.0
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error normalizing image: {str(e)}")
        raise BirdTagError(
            message="Failed to normalize image",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_image_size(file_path: str) -> Tuple[int, int]:
    """
    Get image dimensions
    
    Args:
        file_path (str): Path to image file
    
    Returns:
        Tuple[int, int]: Image dimensions (width, height)
        
    Raises:
        BirdTagError: If getting image size fails
    """
    try:
        if not os.path.exists(file_path):
            raise BirdTagError(
                message="Image file not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        with Image.open(file_path) as img:
            return img.size
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting image size: {str(e)}")
        raise BirdTagError(
            message="Failed to get image size",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def is_valid_image_file(file_path: str) -> bool:
    """
    Check if file is a valid image file
    
    Args:
        file_path (str): Path to image file
    
    Returns:
        bool: True if valid image file
    """
    try:
        if not os.path.exists(file_path):
            return False
            
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def create_thumbnail(
    image_path: str,
    output_path: str,
    size: Tuple[int, int] = (200, 200)
) -> str:
    """
    Create thumbnail from image
    
    Args:
        image_path (str): Path to source image
        output_path (str): Path to save thumbnail
        size (Tuple[int, int]): Thumbnail size
    
    Returns:
        str: Path to thumbnail
        
    Raises:
        BirdTagError: If thumbnail creation fails
    """
    try:
        if not os.path.exists(image_path):
            raise BirdTagError(
                message="Source image not found",
                error_code=ErrorCode.FILE_NOT_FOUND,
                status_code=404
            )
            
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(output_path)
        return output_path
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        raise BirdTagError(
            message="Failed to create thumbnail",
            error_code=ErrorCode.FILE_PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 