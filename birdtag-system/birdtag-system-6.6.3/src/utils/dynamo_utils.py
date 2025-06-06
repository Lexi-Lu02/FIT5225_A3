import boto3
import logging
from boto3.dynamodb.conditions import Key, Attr
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
import json
import time
import uuid
from datetime import datetime
import os

from utils.error_utils import BirdTagError, ErrorCode

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')

# Environment variables with defaults
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'BirdTagMedia')

class DecimalEncoder(json.JSONEncoder):
    """Helper class to convert Decimal to float for JSON serialization"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_table(table_name: str) -> Any:
    """
    Get DynamoDB table resource
    
    Args:
        table_name (str): Name of the DynamoDB table
    
    Returns:
        Table: DynamoDB table resource
    """
    return dynamodb.Table(table_name)

def create_media_record(
    table_name: str,
    file_key: str,
    media_type: str,
    tags: List[str],
    file_url: str,
    thumbnail_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new media record in DynamoDB
    
    Args:
        table_name (str): DynamoDB table name
        file_key (str): S3 file key
        media_type (str): Type of media (image/audio/video)
        tags (List[str]): List of tags
        file_url (str): URL to the media file
        thumbnail_url (str, optional): URL to the thumbnail
        metadata (dict, optional): Additional metadata
    
    Returns:
        Dict[str, Any]: Created record
    """
    try:
        table = get_table(table_name)
        
        # Prepare item
        item = {
            'fileKey': file_key,
            'type': media_type,
            'tags': tags,
            'fileUrl': file_url,
            'status': 'completed',
            'timestamp': int(time.time())
        }
        
        if thumbnail_url:
            item['thumbnailUrl'] = thumbnail_url
        
        if metadata:
            item.update(metadata)
        
        # Put item in table
        table.put_item(Item=item)
        
        return item
    
    except Exception as e:
        logger.error(f"Error creating media record: {str(e)}")
        raise BirdTagError(
            message="Failed to create media record",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def update_media_record(
    table_name: str,
    file_key: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing media record
    
    Args:
        table_name (str): DynamoDB table name
        file_key (str): S3 file key
        updates (dict): Fields to update
    
    Returns:
        Dict[str, Any]: Updated record
    """
    try:
        table = get_table(table_name)
        
        # Build update expression
        update_expr = "SET "
        expr_attr_values = {}
        expr_attr_names = {}
        
        for key, value in updates.items():
            update_expr += f"#{key} = :{key}, "
            expr_attr_values[f":{key}"] = value
            expr_attr_names[f"#{key}"] = key
        
        update_expr = update_expr.rstrip(", ")
        
        # Update item
        response = table.update_item(
            Key={'fileKey': file_key},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_attr_values,
            ExpressionAttributeNames=expr_attr_names,
            ReturnValues="ALL_NEW"
        )
        
        return response.get('Attributes', {})
    
    except Exception as e:
        logger.error(f"Error updating media record: {str(e)}")
        raise BirdTagError(
            message="Failed to update media record",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_media_record(table_name: str, file_key: str) -> Optional[Dict[str, Any]]:
    """
    Get a media record by file key
    
    Args:
        table_name (str): DynamoDB table name
        file_key (str): S3 file key
    
    Returns:
        Optional[Dict[str, Any]]: Media record if found, None otherwise
    """
    try:
        table = get_table(table_name)
        response = table.get_item(Key={'fileKey': file_key})
        return response.get('Item')
    
    except Exception as e:
        logger.error(f"Error getting media record: {str(e)}")
        raise BirdTagError(
            message="Failed to get media record",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def search_by_tags(
    table_name: str,
    tags: List[str],
    start_date: Optional[int] = None,
    end_date: Optional[int] = None,
    limit: int = 20,
    last_evaluated_key: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search media records by tags
    
    Args:
        table_name (str): DynamoDB table name
        tags (List[str]): List of tags to search for
        start_date (int, optional): Start timestamp
        end_date (int, optional): End timestamp
        limit (int): Maximum number of results
        last_evaluated_key (dict, optional): Key for pagination
    
    Returns:
        Dict[str, Any]: Search results and pagination info
    """
    try:
        table = get_table(table_name)
        
        # Build filter expression
        filter_expr = "status = :status"
        expr_attr_values = {':status': 'completed'}
        
        if start_date and end_date:
            filter_expr += " AND #ts BETWEEN :start AND :end"
            expr_attr_values[':start'] = start_date
            expr_attr_values[':end'] = end_date
        
        # Add tag filters
        for i, tag in enumerate(tags):
            filter_expr += f" AND contains(tags, :tag{i})"
            expr_attr_values[f':tag{i}'] = tag
        
        # Query table
        query_params = {
            'FilterExpression': filter_expr,
            'ExpressionAttributeValues': expr_attr_values,
            'ExpressionAttributeNames': {'#ts': 'timestamp'},
            'Limit': limit
        }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
        
        response = table.scan(**query_params)
        
        return {
            'items': response.get('Items', []),
            'lastEvaluatedKey': response.get('LastEvaluatedKey')
        }
    
    except Exception as e:
        logger.error(f"Error searching by tags: {str(e)}")
        raise BirdTagError(
            message="Failed to search by tags",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def search_by_species(
    table_name: str,
    species: str,
    limit: int = 20,
    last_evaluated_key: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Search media records by species
    
    Args:
        table_name (str): DynamoDB table name
        species (str): Species to search for
        limit (int): Maximum number of results
        last_evaluated_key (dict, optional): Key for pagination
    
    Returns:
        Dict[str, Any]: Search results and pagination info
    """
    try:
        table = get_table(table_name)
        
        # Query using GSI
        query_params = {
            'IndexName': 'species-index',
            'KeyConditionExpression': 'species = :species',
            'ExpressionAttributeValues': {':species': species},
            'Limit': limit
        }
        
        if last_evaluated_key:
            query_params['ExclusiveStartKey'] = last_evaluated_key
        
        response = table.query(**query_params)
        
        return {
            'items': response.get('Items', []),
            'lastEvaluatedKey': response.get('LastEvaluatedKey')
        }
    
    except Exception as e:
        logger.error(f"Error searching by species: {str(e)}")
        raise BirdTagError(
            message="Failed to search by species",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def delete_media_record(table_name: str, file_key: str) -> None:
    """
    Delete a media record
    
    Args:
        table_name (str): DynamoDB table name
        file_key (str): S3 file key
    """
    try:
        table = get_table(table_name)
        table.delete_item(Key={'fileKey': file_key})
    except Exception as e:
        logger.error(f"Error deleting media record: {str(e)}")
        raise BirdTagError(
            message="Failed to delete media record",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_user_stats(user_id: str) -> Dict[str, Any]:
    """
    Get user statistics
    
    Args:
        user_id (str): User ID
    
    Returns:
        Dict[str, Any]: User statistics
    """
    try:
        table = get_table(DYNAMODB_TABLE)
        
        # Query user's media records
        response = table.query(
            IndexName='user-index',
            KeyConditionExpression='userId = :userId',
            ExpressionAttributeValues={':userId': user_id}
        )
        
        items = response.get('Items', [])
        
        # Calculate statistics
        total_media = len(items)
        media_by_type = {}
        tags_count = {}
        
        for item in items:
            media_type = item.get('type', 'unknown')
            media_by_type[media_type] = media_by_type.get(media_type, 0) + 1
            
            for tag in item.get('tags', []):
                tags_count[tag] = tags_count.get(tag, 0) + 1
        
        return {
            'userId': user_id,
            'totalMedia': total_media,
            'mediaByType': media_by_type,
            'topTags': sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        raise BirdTagError(
            message="Failed to get user statistics",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_system_stats() -> Dict[str, Any]:
    """
    Get system-wide statistics
    
    Returns:
        Dict[str, Any]: System statistics
    """
    try:
        table = get_table(DYNAMODB_TABLE)
        
        # Scan all records
        response = table.scan()
        items = response.get('Items', [])
        
        # Calculate statistics
        total_media = len(items)
        media_by_type = {}
        tags_count = {}
        species_count = {}
        
        for item in items:
            media_type = item.get('type', 'unknown')
            media_by_type[media_type] = media_by_type.get(media_type, 0) + 1
            
            for tag in item.get('tags', []):
                tags_count[tag] = tags_count.get(tag, 0) + 1
            
            species = item.get('species')
            if species:
                species_count[species] = species_count.get(species, 0) + 1
        
        return {
            'totalMedia': total_media,
            'mediaByType': media_by_type,
            'topTags': sorted(tags_count.items(), key=lambda x: x[1], reverse=True)[:20],
            'topSpecies': sorted(species_count.items(), key=lambda x: x[1], reverse=True)[:20]
        }
    
    except Exception as e:
        logger.error(f"Error getting system stats: {str(e)}")
        raise BirdTagError(
            message="Failed to get system statistics",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def get_species_stats(species: str) -> Dict[str, Any]:
    """
    Get statistics for a specific species
    
    Args:
        species (str): Species name
    
    Returns:
        Dict[str, Any]: Species statistics
    """
    try:
        table = get_table(DYNAMODB_TABLE)
        
        # Query species records
        response = table.query(
            IndexName='species-index',
            KeyConditionExpression='species = :species',
            ExpressionAttributeValues={':species': species}
        )
        
        items = response.get('Items', [])
        
        # Calculate statistics
        total_media = len(items)
        media_by_type = {}
        confidence_sum = 0
        confidence_count = 0
        
        for item in items:
            media_type = item.get('type', 'unknown')
            media_by_type[media_type] = media_by_type.get(media_type, 0) + 1
            
            confidence = item.get('confidence')
            if confidence is not None:
                confidence_sum += confidence
                confidence_count += 1
        
        return {
            'species': species,
            'totalMedia': total_media,
            'mediaByType': media_by_type,
            'averageConfidence': confidence_sum / confidence_count if confidence_count > 0 else 0
        }
    
    except Exception as e:
        logger.error(f"Error getting species stats: {str(e)}")
        raise BirdTagError(
            message="Failed to get species statistics",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 