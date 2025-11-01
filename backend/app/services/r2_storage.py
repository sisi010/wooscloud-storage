"""
Cloudflare R2 Storage Service
S3-compatible object storage for large data
"""

import boto3
from botocore.client import Config
from typing import Optional, Dict, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class R2Storage:
    """Cloudflare R2 storage client"""
    
    def __init__(
        self,
        account_id: str,
        access_key: str,
        secret_key: str,
        bucket_name: str
    ):
        """
        Initialize R2 storage
        
        Args:
            account_id: Cloudflare account ID
            access_key: R2 access key
            secret_key: R2 secret key
            bucket_name: R2 bucket name
        """
        self.bucket_name = bucket_name
        
        # Create S3 client for R2
        self.client = boto3.client(
            's3',
            endpoint_url=f'https://{account_id}.r2.cloudflarestorage.com',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        
        logger.info(f"R2 storage initialized for bucket: {bucket_name}")
    
    def put_json(self, key: str, data: Dict[str, Any]) -> str:
        """
        Store JSON data in R2
        
        Args:
            key: Object key (path)
            data: JSON data to store
        
        Returns:
            Object key
        """
        try:
            json_data = json.dumps(data, ensure_ascii=False)
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=json_data.encode('utf-8'),
                ContentType='application/json',
                Metadata={
                    'uploaded_at': datetime.utcnow().isoformat(),
                    'size_bytes': str(len(json_data))
                }
            )
            
            logger.info(f"Stored JSON in R2: {key}")
            return key
            
        except Exception as e:
            logger.error(f"Failed to store in R2: {e}")
            raise
    
    def get_json(self, key: str) -> Dict[str, Any]:
        """
        Retrieve JSON data from R2
        
        Args:
            key: Object key
        
        Returns:
            JSON data
        """
        try:
            response = self.client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            json_data = response['Body'].read().decode('utf-8')
            data = json.loads(json_data)
            
            logger.info(f"Retrieved JSON from R2: {key}")
            return data
            
        except Exception as e:
            logger.error(f"Failed to retrieve from R2: {e}")
            raise
    
    def delete(self, key: str) -> bool:
        """
        Delete object from R2
        
        Args:
            key: Object key
        
        Returns:
            True if successful
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            logger.info(f"Deleted from R2: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete from R2: {e}")
            raise
    
    def list_objects(self, prefix: str = "", max_keys: int = 1000) -> list:
        """
        List objects in R2
        
        Args:
            prefix: Key prefix to filter
            max_keys: Maximum number of keys
        
        Returns:
            List of object keys
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            keys = [obj['Key'] for obj in response.get('Contents', [])]
            logger.info(f"Listed {len(keys)} objects from R2")
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list R2 objects: {e}")
            raise
    
    def get_object_size(self, key: str) -> int:
        """
        Get object size in bytes
        
        Args:
            key: Object key
        
        Returns:
            Size in bytes
        """
        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return response['ContentLength']
            
        except Exception as e:
            logger.error(f"Failed to get object size: {e}")
            return 0