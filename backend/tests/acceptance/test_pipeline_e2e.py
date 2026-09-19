import importlib.util
import sys
import os
import json
import pytest
import boto3
from moto import mock_aws
from PIL import Image
import io

# load lambda/handler.py because lambda is a reserved keyword
spec = importlib.util.spec_from_file_location("handler", "backend/lambda/handler.py")
handler_module = importlib.util.module_from_spec(spec)
sys.modules["handler"] = handler_module
spec.loader.exec_module(handler_module)
from handler import handler

@mock_aws
def test_numeric_fields_e2e(mocker):
    os.environ['REGION'] = 'ap-south-1'
    os.environ['AWS_DEFAULT_REGION'] = 'ap-south-1'
    os.environ['TABLE_NAME'] = 'test-scans'
    handler_module.TABLE_NAME = 'test-scans'
    
    # Setup Moto
    s3 = boto3.client('s3', region_name='ap-south-1')
    s3.create_bucket(Bucket='labelcheck-uploads', CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    s3.create_bucket(Bucket='labelcheck-outputs', CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'})
    
    dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
    dynamodb.create_table(
        TableName=os.environ['TABLE_NAME'],
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[
            {'AttributeName': 'scan_id', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1_pk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi1_sk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi2_pk', 'AttributeType': 'S'},
            {'AttributeName': 'gsi2_sk', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexes=[
            {
                'IndexName': 'gsi1',
                'KeySchema': [
                    {'AttributeName': 'gsi1_pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'gsi1_sk', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            },
            {
                'IndexName': 'gsi2',
                'KeySchema': [
                    {'AttributeName': 'gsi2_pk', 'KeyType': 'HASH'},
                    {'AttributeName': 'gsi2_sk', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # 1. POST /upload
    post_event = {
        'requestContext': {
            'http': {'method': 'POST', 'path': '/upload'}
        },
        'body': json.dumps({
            'filename': 'test.jpg',
            'content_type': 'image/jpeg',
            'label_width_mm': 90.5
        })
    }
    
    post_res = handler(post_event, {})
    assert post_res['statusCode'] == 200
    body = json.loads(post_res['body'])
    scan_id = body['scan_id']
    
    # 2. Upload to S3 directly (skip presigned URL for Moto test)
    img = Image.new('RGB', (100, 100), color='white')
    buf = io.BytesIO()
    img.save(buf, format='JPEG')
    s3_key = f"uploads/{scan_id}.jpg"
    s3.put_object(Bucket='labelcheck-uploads', Key=s3_key, Body=buf.getvalue())
    
    # 3. S3 Event
    s3_event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': s3_key, 'size': len(buf.getvalue())}
            }
        }]
    }
    
    # Mock gauntlet (just mock BEDROCK)
    def dummy_client(ibytes, prompt, model_id, schema):
        return {
            "schema_version": "1.0",
            "source_type": "photo",
            "image": {"width": 100, "height": 100},
            "language": "en",
            "fields": {
                "net_quantity": {"raw": "100 g", "parsed": {"value": 100.5, "unit": "g"}, "confidence": 0.9, "box": [0,0,1,1]}
            }
        }
    mocker.patch('src.pipeline.main.run_pipeline', return_value={
        'status': 'DONE',
        'summary': {'pass': 1, 'fail': 0, 'na': 10, 'needs_review': 0, 'exempt': 0, 'found_declarations': 1},
        'results': [],
        'artifacts': {},
        'exemption': None,
        'extraction': dummy_client(None, None, None, None),
        'product': {}
    })
    
    handler(s3_event, {})
    
    # 4. Poll GET /scans/{scan_id}
    get_event = {
        'requestContext': {
            'http': {'method': 'GET', 'path': f'/scans/{scan_id}'}
        },
        'pathParameters': {'scan_id': scan_id}
    }
    
    get_res = handler(get_event, {})
    assert get_res['statusCode'] == 200
    
    get_body = json.loads(get_res['body'])
    assert get_body['input']['label_width_mm'] == 90.5
    assert get_body['extraction']['fields']['net_quantity']['parsed']['value'] == 100.5
