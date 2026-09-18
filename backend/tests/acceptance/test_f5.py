import pytest
import os
import json
import boto3
from moto import mock_aws
from src.ingestion.upload import generate_scan_id, create_pending_record
from src.ingestion.claim import claim_scan
from datetime import datetime, timezone, timedelta
import dateutil.parser

os.environ['REGION'] = 'us-east-1'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['TABLE_NAME'] = 'test_scans'
os.environ['UPLOADS_BUCKET'] = 'labelcheck-uploads'
os.environ['OUTPUTS_BUCKET'] = 'labelcheck-outputs'
os.environ['WEB_BUCKET'] = 'labelcheck-web'

# Note: we need to use lambda_ because 'lambda' is a reserved word in Python
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
import importlib.util
spec = importlib.util.spec_from_file_location("handler", "backend/lambda/handler.py")
handler_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handler_module)
handler = handler_module.handler

@pytest.fixture
def setup_aws():
    with mock_aws():
        dynamodb = boto3.client('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='test_scans',
            KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='labelcheck-uploads')
        
        yield {'dynamodb': dynamodb, 's3': s3}

@mock_aws
def test_f5_wrong_content_type(setup_aws):
    event = {
        'requestContext': {'http': {'method': 'POST', 'path': '/upload'}},
        'body': json.dumps({'filename': 'test.txt', 'content_type': 'text/plain'})
    }
    res = handler(event, None)
    assert res['statusCode'] == 400
    assert 'Unsupported content_type' in json.loads(res['body'])['error']['message']

@mock_aws
def test_f5_1000_scan_ids():
    import re
    ids = set()
    for _ in range(1000):
        scan_id = generate_scan_id()
        assert re.match(r'^SC-[A-HJ-NP-Z2-9]{6}$', scan_id)
        ids.add(scan_id)
    assert len(ids) == 1000

@mock_aws
def test_f5_duplicate_events(setup_aws, mocker):
    scan_id = create_pending_record('test_scans', 'test.jpg', 'image/jpeg')
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': f'uploads/{scan_id}.jpg', 'size': 1024}
            }
        }]
    }
    
    spy = mocker.spy(handler_module, 'mark_terminal')
    
    # First delivery
    res1 = handler(event, None)
    assert res1['status'] == 'success'
    assert spy.call_count == 1
    
    # Second delivery
    res2 = handler(event, None)
    assert res2['status'] == 'skipped'
    assert spy.call_count == 1  # Not called again
    
@mock_aws
def test_f5_no_record_phantom(setup_aws):
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': 'uploads/SC-ABCDEF.jpg', 'size': 1024}
            }
        }]
    }
    res = handler(event, None)
    assert res['status'] == 'skipped'
    
    # Assert no record created
    resp = setup_aws['dynamodb'].get_item(TableName='test_scans', Key={'scan_id': {'S': 'SC-ABCDEF'}})
    assert 'Item' not in resp

@mock_aws
def test_f5_late_event_after_terminal(setup_aws):
    scan_id = create_pending_record('test_scans', 'test.jpg', 'image/jpeg')
    
    setup_aws['dynamodb'].update_item(
        TableName='test_scans',
        Key={'scan_id': {'S': scan_id}},
        UpdateExpression='SET #st = :done',
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':done': {'S': 'DONE'}}
    )
    
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': f'uploads/{scan_id}.jpg', 'size': 1024}
            }
        }]
    }
    res = handler(event, None)
    assert res['status'] == 'skipped'
    
@mock_aws
def test_f5_oversized_file(setup_aws):
    scan_id = create_pending_record('test_scans', 'test.jpg', 'image/jpeg')
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': f'uploads/{scan_id}.jpg', 'size': 20971520 + 1}
            }
        }]
    }
    res = handler(event, None)
    assert res['status'] == 'oversized'
    
    resp = setup_aws['dynamodb'].get_item(TableName='test_scans', Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'OVERSIZED_FILE'

@mock_aws
def test_f5_pipeline_exception(setup_aws, mocker):
    scan_id = create_pending_record('test_scans', 'test.jpg', 'image/jpeg')
    event = {
        'Records': [{
            's3': {
                'bucket': {'name': 'labelcheck-uploads'},
                'object': {'key': f'uploads/{scan_id}.jpg', 'size': 1024}
            }
        }]
    }
    
    mocker.patch('src.pipeline.main.run_pipeline', side_effect=Exception("Boom"))
    
    res = handler(event, None)
    assert res['status'] == 'success' # Lambda succeeds, error written to DB
    
    resp = setup_aws['dynamodb'].get_item(TableName='test_scans', Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'INTERNAL'

