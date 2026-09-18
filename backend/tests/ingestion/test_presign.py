import pytest
import os
import boto3
from moto import mock_aws
from src.ingestion.presign import presign_upload

@mock_aws
def test_presign_upload():
    os.environ['REGION'] = 'us-east-1'
    # moto doesn't actually need the bucket to exist to generate a presigned url, 
    # but we will just check if the URL format is correct.
    url = presign_upload('test-bucket', 'uploads/SC-123456.jpg', 'image/jpeg')
    
    assert 'https://s3.amazonaws.com/test-bucket/uploads/SC-123456.jpg' in url or 'https://test-bucket.s3.amazonaws.com/uploads/SC-123456.jpg' in url
    assert 'AWSAccessKeyId' in url or 'X-Amz-Credential' in url
