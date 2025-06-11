import boto3
import json
from botocore.exceptions import NoCredentialsError, ClientError
from typing import Dict, Any, Optional, List
from .artifact_repository import ArtifactRepository, CommonEncoder

class S3ArtifactRepository(ArtifactRepository):
    def __init__(self, bucket_name: str, endpoint_url: str, access_key: str, secret_key: str):
        """
        Initialize the S3 artifact repository
        
        Args:
            bucket_name: Name of the S3 bucket
            endpoint_url: MinIO endpoint URL
            access_key: Access key for MinIO
            secret_key: Secret key for MinIO
        """
        super().__init__()
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )

    def store(self, artifact_id: str, type: str, data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Store artifact in S3 and return its version identifier
        
        Args:
            artifact_id: Unique identifier of the artifact
            data: Data to be stored
            metadata: Optional metadata
            
        Returns:
            Version identifier
        """
        content_hash = self._compute_content_hash(data)
        object_key = f"{type}/{artifact_id}/{content_hash}.json"

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=object_key,
                Body=json.dumps(data, cls=CommonEncoder),
                ContentType='application/json'
            )
        except (NoCredentialsError, ClientError) as e:
            print(f"Error storing artifact: {e}")
            return "failure"

        # Optionally, you can save metadata or versioning information in a separate index
        return content_hash  # Return the content hash as the version identifier

    def retrieve(self, version_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve artifact from S3 based on version ID
        
        Args:
            version_id: Version identifier
            
        Returns:
            Stored data, or None if it doesn't exist
        """
        # Assuming version_id is the content hash
        object_key = f"artifact/{version_id}.json"
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
            data = response['Body'].read().decode('utf-8')
            return json.loads(data)
        except ClientError as e:
            print(f"Error retrieving artifact: {e}")
            return None

    def retrieve_latest_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the latest artifact from S3 based on artifact ID
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            Stored data, or None if it doesn't exist
        """
        # This example assumes the latest artifact is the one with the highest content hash
        # You may need to implement a more sophisticated versioning strategy
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=f"artifact/{artifact_id}/")
            if 'Contents' in response:
                latest_object = max(response['Contents'], key=lambda x: x['LastModified'])
                object_key = latest_object['Key']
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=object_key)
                data = response['Body'].read().decode('utf-8')
                return json.loads(data)
        except ClientError as e:
            print(f"Error retrieving latest artifact: {e}")
            return None

    def get_versions(self, artifact_id: str) -> List[Dict[str, Any]]:
        """
        Get information about all versions of an artifact from S3
        
        Args:
            artifact_id: Artifact identifier
            
        Returns:
            List of version information
        """
        versions = []
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.bucket_name, Prefix=f"artifact/{artifact_id}/")
            if 'Contents' in response:
                for obj in response['Contents']:
                    version_id = obj['Key'].split('/')[-1].replace('.json', '')
                    versions.append({
                        'version_id': version_id,
                        'last_modified': obj['LastModified'].isoformat()
                    })
        except ClientError as e:
            print(f"Error retrieving versions: {e}")
        return versions
