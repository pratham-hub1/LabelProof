import pytest
import os
import boto3
from moto import mock_aws
from src.pipeline.main import run_pipeline
from PIL import Image
import io

@mock_aws
def test_pipeline_end_to_end():
    s3 = boto3.client('s3', region_name='ap-south-1')
    s3.create_bucket(Bucket='labelcheck-uploads', CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    s3.create_bucket(Bucket='labelcheck-outputs', CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    os.environ['OUTPUTS_BUCKET'] = 'labelcheck-outputs'
    os.environ['REGION'] = 'ap-south-1'
    
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    s3.put_object(Bucket='labelcheck-uploads', Key='uploads/SC-E2E.jpg', Body=buf.getvalue())
    
    scan_fields = {
        'input': {'content_type': 'image/jpeg'}
    }
    
    res = run_pipeline('SC-E2E', 'labelcheck-uploads', 'uploads/SC-E2E.jpg', len(buf.getvalue()), scan_fields)
    
    assert res['status'] in ['DONE', 'NEEDS_REVIEW']
    assert 'extraction' in res
    assert 'artifacts' in res
    
    # Verify artifacts were written to output bucket
    objs = s3.list_objects_v2(Bucket='labelcheck-outputs', Prefix='outputs/reports/SC-E2E/')
    assert len(objs['Contents']) == 5
