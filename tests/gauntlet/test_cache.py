import pytest
import boto3
from moto import mock_aws
from botocore.exceptions import ClientError
from src.gauntlet.cache import get_extraction_cache, put_extraction_cache

@pytest.fixture
def s3_setup():
    with mock_aws():
        s3 = boto3.client('s3', region_name='ap-south-1')
        s3.create_bucket(
            Bucket='labelcheck-uploads',
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        yield s3

def test_cache_miss(s3_setup):
    result = get_extraction_cache('labelcheck-uploads', 'nonexistent-etag', s3_client=s3_setup)
    assert result is None

def test_cache_put_and_get(s3_setup):
    data = {"fields": {"mrp": {"raw": "MRP 20"}}}
    etag = '"my-test-etag"'
    
    # Put
    put_extraction_cache('labelcheck-uploads', etag, data, s3_client=s3_setup)
    
    # Get
    result = get_extraction_cache('labelcheck-uploads', etag, s3_client=s3_setup)
    assert result == data

def test_cache_other_errors(s3_setup, mocker):
    # Simulate an error other than NoSuchKey
    mocker.patch.object(s3_setup, 'get_object', side_effect=ClientError({'Error': {'Code': 'AccessDenied'}}, 'GetObject'))
    
    with pytest.raises(ClientError):
        get_extraction_cache('labelcheck-uploads', 'my-test-etag', s3_client=s3_setup)
