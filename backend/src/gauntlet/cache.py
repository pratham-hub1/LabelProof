import json
import boto3
from botocore.exceptions import ClientError

def get_extraction_cache(bucket_name, etag, s3_client=None):
    """
    Gets extraction from the cache.
    Key: cache/{etag}.json
    """
    if s3_client is None:
        s3_client = boto3.client('s3')
        
    # ETag from S3 sometimes has quotes, strip them
    clean_etag = etag.strip('"\'')
    key = f"cache/{clean_etag}.json"
    
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return json.loads(response['Body'].read().decode('utf-8'))
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchKey':
            return None
        raise

def put_extraction_cache(bucket_name, etag, extraction_data, s3_client=None):
    """
    Puts extraction into the cache.
    Key: cache/{etag}.json
    """
    if s3_client is None:
        s3_client = boto3.client('s3')
        
    clean_etag = etag.strip('"\'')
    key = f"cache/{clean_etag}.json"
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=json.dumps(extraction_data).encode('utf-8'),
        ContentType='application/json'
    )
