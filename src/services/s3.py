"""
S3 Service

Handles AWS S3 operations for file uploads and downloads.
"""

from typing import List, Optional
import aioboto3
from botocore.exceptions import ClientError

from src.config import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class S3Service:
    """AWS S3 service with async support"""

    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        self.session = aioboto3.Session(
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )

    async def upload_file(self, content: str, key: str, content_type: str = "text/plain") -> str:
        """
        Upload file to S3.

        Args:
            content: File content (string or bytes)
            key: S3 key (path)
            content_type: MIME type of the content

        Returns:
            str: S3 URI
        """
        try:
            async with self.session.client("s3") as s3:
                if isinstance(content, str):
                    content = content.encode("utf-8")

                await s3.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                )
                logger.info(f"Successfully uploaded file to S3: s3://{self.bucket_name}/{key}")
                return f"s3://{self.bucket_name}/{key}"
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise

    async def download_file(self, key: str) -> str:
        """
        Download file from S3.

        Args:
            key: S3 key (path)

        Returns:
            str: File content
        """
        try:
            async with self.session.client("s3") as s3:
                response = await s3.get_object(Bucket=self.bucket_name, Key=key)
                content = await response["Body"].read()
                logger.info(f"Successfully downloaded file from S3: s3://{self.bucket_name}/{key}")
                return content.decode("utf-8")
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise

    async def list_objects(self, prefix: str = "", max_keys: int = 1000) -> List[str]:
        """
        List files in S3 with prefix.

        Args:
            prefix: S3 prefix
            max_keys: Maximum number of keys to return

        Returns:
            list[str]: List of S3 keys
        """
        try:
            async with self.session.client("s3") as s3:
                response = await s3.list_objects_v2(
                    Bucket=self.bucket_name, Prefix=prefix, MaxKeys=max_keys
                )
                if "Contents" in response:
                    keys = [obj["Key"] for obj in response["Contents"]]
                    logger.info(f"Found {len(keys)} objects with prefix: {prefix}")
                    return keys
                return []
        except ClientError as e:
            logger.error(f"Failed to list objects from S3: {e}")
            raise

    async def object_exists(self, key: str) -> bool:
        """
        Check if an object exists in S3.

        Args:
            key: S3 key (path)

        Returns:
            bool: True if object exists, False otherwise
        """
        try:
            async with self.session.client("s3") as s3:
                await s3.head_object(Bucket=self.bucket_name, Key=key)
                return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Failed to check object existence: {e}")
            raise

    async def delete_file(self, key: str) -> bool:
        """
        Delete file from S3.

        Args:
            key: S3 key (path)

        Returns:
            bool: True if successful
        """
        try:
            async with self.session.client("s3") as s3:
                await s3.delete_object(Bucket=self.bucket_name, Key=key)
                logger.info(f"Successfully deleted file from S3: s3://{self.bucket_name}/{key}")
                return True
        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            raise


# Global instance
s3_service = S3Service()
