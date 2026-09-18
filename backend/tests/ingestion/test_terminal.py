import pytest
import os
import boto3
from moto import mock_aws
from src.ingestion.upload import create_pending_record
from src.ingestion.claim import claim_scan
from src.ingestion.terminal import mark_terminal

@mock_aws
def test_mark_terminal_success():
    os.environ['REGION'] = 'us-east-1'
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    table_name = 'test_scans'
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    scan_id = create_pending_record(table_name, 'test.jpg', 'image/jpeg')
    claim_scan(table_name, scan_id, 1024)
    
    # Mark terminal
    result = mark_terminal(
        table_name=table_name,
        scan_id=scan_id,
        status='DONE',
        summary={'pass': 1, 'fail': 0}
    )
    
    assert result == True
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'DONE'
    assert 'error' in resp['Item'] and 'NULL' in resp['Item']['error']
    assert resp['Item']['summary']['M']['pass']['N'] == '1'
    
@mock_aws
def test_mark_terminal_error():
    os.environ['REGION'] = 'us-east-1'
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    table_name = 'test_scans'
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    scan_id = create_pending_record(table_name, 'test.jpg', 'image/jpeg')
    
    # from_pending=True
    result = mark_terminal(
        table_name=table_name,
        scan_id=scan_id,
        status='FAILED',
        error_code='UPLOAD_TIMEOUT',
        from_pending=True
    )
    
    assert result == True
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'UPLOAD_TIMEOUT'
