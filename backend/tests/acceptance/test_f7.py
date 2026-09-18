import pytest
import os
import json
import boto3
from moto import mock_aws
from src.api.router import route_api
from src.ingestion.upload import create_pending_record
from src.ingestion.terminal import mark_terminal

@pytest.fixture
def mock_dynamodb():
    with mock_aws():
        dynamodb = boto3.client('dynamodb', region_name='ap-south-1')
        dynamodb.create_table(
            TableName='labelcheck-scans',
            KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'scan_id', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1_pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi1_sk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2_pk', 'AttributeType': 'S'},
                {'AttributeName': 'gsi2_sk', 'AttributeType': 'S'},
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
        os.environ['TABLE_NAME'] = 'labelcheck-scans'
        os.environ['REGION'] = 'ap-south-1'
        yield dynamodb

def make_event(path, method='GET', qsp=None):
    return {
        'requestContext': {
            'http': {
                'method': method,
                'path': path
            }
        },
        'queryStringParameters': qsp or {}
    }

def test_f7_criteria_11(mock_dynamodb):
    # 11: Unknown path -> 404, wrong method -> 405
    resp = route_api(make_event('/foo'), None)
    assert resp['statusCode'] == 404
    assert json.loads(resp['body'])['error']['code'] == 'NOT_FOUND'
    
    resp = route_api(make_event('/scans', 'POST'), None)
    assert resp['statusCode'] == 405
    assert json.loads(resp['body'])['error']['code'] == 'METHOD_NOT_ALLOWED'

def test_f7_criteria_1_2_3_4_5_8_12_13(mock_dynamodb, mocker):
    import time
    for i in range(25):
        scan_id = f"SC-{i:03d}"
        mocker.patch('src.ingestion.upload.generate_scan_id', return_value=scan_id)
        
        create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
        
        # update slightly in time to give deterministic ordering
        # created_at is normally populated by create_pending_record. We can just use the created_at that it set.
        
        # For terminal, we will fetch it
        db = boto3.resource('dynamodb', region_name='ap-south-1')
        item = db.Table('labelcheck-scans').get_item(Key={'scan_id': scan_id})['Item']
        created_at = item['created_at']
        
        # Make SC-005 have R5 fail
        # Make SC-010 have brand "haldiram"
        # Make SC-015 have product "haldiram mix"
        status = 'DONE'
        results = {}
        if i == 5:
            results['R5'] = {'status': 'FAIL'}
        if i == 6:
            results['R5'] = {'status': 'FAIL'}
            status = 'NEEDS_REVIEW'
            
        product = {}
        if i == 10:
            product['brand_guess'] = "Haldiram's!" # tests normalize_key
        if i == 15:
            product['product_name'] = "Haldiram mix"
            
        db.Table('labelcheck-scans').update_item(
            Key={'scan_id': scan_id},
            UpdateExpression="SET #st = :p",
            ExpressionAttributeNames={'#st': 'status'},
            ExpressionAttributeValues={':p': 'PROCESSING'}
        )
        
        mark_terminal(
            table_name='labelcheck-scans',
            scan_id=scan_id,
            status=status,
            results=results,
            product=product,
            created_at=created_at
        )
        
    # Criteria 1: pagination
    res1 = route_api(make_event('/scans', qsp={'limit': '10'}), None)
    b1 = json.loads(res1['body'])
    assert len(b1['items']) == 10
    assert 'next_key' in b1
    
    res2 = route_api(make_event('/scans', qsp={'limit': '10', 'last_key': b1['next_key']}), None)
    b2 = json.loads(res2['body'])
    assert len(b2['items']) == 10
    
    res3 = route_api(make_event('/scans', qsp={'limit': '10', 'last_key': b2['next_key']}), None)
    b3 = json.loads(res3['body'])
    assert len(b3['items']) == 5
    assert b3.get('next_key') is None
    
    all_items = b1['items'] + b2['items'] + b3['items']
    assert len(all_items) == 25
    
    # Criteria 8: No internal keys
    for it in all_items:
        assert 'gsi1_pk' not in it
        assert 'brand_key' not in it
        assert 'failed_rules' not in it
        
    # Criteria 2: status filter
    res = route_api(make_event('/scans', qsp={'status': 'NEEDS_REVIEW', 'limit': '100'}), None)
    assert len(json.loads(res['body'])['items']) == 1
    
    # Criteria 3: rule_id filter
    res = route_api(make_event('/scans', qsp={'rule_id': 'R5', 'limit': '100'}), None)
    items = json.loads(res['body'])['items']
    assert len(items) == 2
    
    # Criteria 4: search leg GSI-2 vs Fallback
    res = route_api(make_event('/scans', qsp={'query': 'haldiram'}), None)
    items = json.loads(res['body'])['items']
    # SC-010 is brand_guess (GSI-2). SC-015 is product_name (Fallback)
    # Wait, if GSI-2 matches, does it fallback? "empty result -> base-table Scan".
    # Since haldiram matches GSI-2 for SC-010, the first request returns SC-010!
    assert len(items) == 1
    assert items[0]['scan_id'] == 'SC-010'
    
    # What if we search for 'mix' (only matches product_name -> Scan fallback)
    res = route_api(make_event('/scans', qsp={'query': 'mix'}), None)
    items = json.loads(res['body'])['items']
    assert len(items) == 1
    assert items[0]['scan_id'] == 'SC-015'
    
def test_f7_criteria_6(mock_dynamodb):
    # 6: Garbage cursor
    res = route_api(make_event('/scans', qsp={'last_key': 'abc123!@#'}), None)
    assert res['statusCode'] == 400
    
def test_f7_criteria_9(mock_dynamodb, mocker):
    # 9: GET /reports: PENDING -> 404, terminal -> 302, unknown -> 404
    mocker.patch('src.ingestion.upload.generate_scan_id', return_value='SC-R')
    create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
    res = route_api(make_event('/reports/SC-R.pdf'), None)
    assert res['statusCode'] == 404
    
    db = boto3.resource('dynamodb', region_name='ap-south-1')
    db.Table('labelcheck-scans').update_item(
        Key={'scan_id': 'SC-R'},
        UpdateExpression="SET #st = :p",
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':p': 'PROCESSING'}
    )
    
    mark_terminal(
        'labelcheck-scans', 'SC-R', 'DONE', 
        artifacts={'report_pdf': 'outputs/reports/SC-R/report.pdf'}
    )
    
    res = route_api(make_event('/reports/SC-R.pdf'), None)
    assert res['statusCode'] == 302
    assert res['headers']['Location'] == 'https://labelcheck-outputs.s3.ap-south-1.amazonaws.com/outputs/reports/SC-R/report.pdf'

def test_f7_criteria_7(mock_dynamodb, mocker):
    # 7: Stats
    mocker.patch('src.ingestion.upload.generate_scan_id', return_value='SC-S1')
    create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
    # PENDING -> no summary
    
    # DONE -> summary
    mocker.patch('src.ingestion.upload.generate_scan_id', return_value='SC-S2')
    create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
    db = boto3.resource('dynamodb', region_name='ap-south-1')
    db.Table('labelcheck-scans').update_item(Key={'scan_id': 'SC-S2'}, UpdateExpression="SET #st = :p", ExpressionAttributeNames={'#st': 'status'}, ExpressionAttributeValues={':p': 'PROCESSING'})
    mark_terminal(
        'labelcheck-scans', 'SC-S2', 'DONE', 
        summary={'pass': 1, 'fail': 1, 'na': 0, 'needs_review': 0, 'exempt': 0},
        results={'R1': {'status': 'PASS'}, 'R2': {'status': 'FAIL'}}
    )
    
    res = route_api(make_event('/stats'), None)
    b = json.loads(res['body'])
    assert b['total_scans'] == 2 # 1 PENDING + 1 DONE
    assert b['overall']['pass'] == 1
    assert b['by_rule']['R2']['fail'] == 1
    assert b['most_failed_rules'] == [{'rule_id': 'R2', 'count': 1}]

def test_f7_criteria_10_stale(mock_dynamodb, mocker):
    mocker.patch('src.ingestion.upload.generate_scan_id', return_value='SC-STALE')
    create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
    db = boto3.resource('dynamodb', region_name='ap-south-1')
    
    # Force it to be old PROCESSING
    db.Table('labelcheck-scans').update_item(
        Key={'scan_id': 'SC-STALE'},
        UpdateExpression='SET #st = :p, updated_at = :old',
        ExpressionAttributeNames={'#st': 'status'},
        ExpressionAttributeValues={':p': 'PROCESSING', ':old': '2000-01-01T00:00:00Z'}
    )
    
    res = route_api({'requestContext': {'http': {'method': 'GET', 'path': '/scans/SC-STALE'}}}, None)
    assert res['statusCode'] == 200
    b = json.loads(res['body'])
    assert b['status'] == 'FAILED'
    assert b['error']['code'] == 'STALE_PROCESSING'

def test_f7_criteria_10_pending(mock_dynamodb, mocker):
    mocker.patch('src.ingestion.upload.generate_scan_id', return_value='SC-PENDING')
    create_pending_record('labelcheck-scans', 'test.jpg', 'image/jpeg')
    
    # We mock reap_stale_pending so it doesn't try to call S3 head_object in the mock without setup
    # actually mock_aws s3 might just return 404 which is fine, it will mark it UPLOAD_TIMEOUT if it's old.
    # But if it's new (which it is, since we just created it), it should just return the PENDING record.
    res = route_api({'requestContext': {'http': {'method': 'GET', 'path': '/scans/SC-PENDING'}}}, None)
    assert res['statusCode'] == 200
    b = json.loads(res['body'])
    assert b['status'] == 'PENDING'
    # Ensure missing fields are present as null
    assert 'artifacts' in b and b['artifacts'] is None
    assert 'exemption' in b and b['exemption'] is None
    assert 'extraction' in b and b['extraction'] is None
