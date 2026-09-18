import boto3
import os
import json

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ingestion.config')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

def presign_upload(bucket: str, key: str, content_type: str) -> str:
    """
    Generates a presigned PUT URL for the given key and content_type.
    """
    s3 = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-south-1'))
    
    url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': bucket,
            'Key': key,
            'ContentType': content_type
        },
        ExpiresIn=CONFIG['presign_expiry_seconds']
    )
    return url
