import pytest
import os
import boto3
from moto import mock_aws
from datetime import datetime, timezone, timedelta
from src.ingestion.upload import create_pending_record
from src.ingestion.claim import claim_scan
from src.ingestion.reapers import reap_stale_processing, reap_stale_pending

@mock_aws
def test_reap_stale_processing():
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
    
    # artificially age the record
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat().replace('+00:00', 'Z')
    dynamodb.update_item(
        TableName=table_name,
        Key={'scan_id': {'S': scan_id}},
        UpdateExpression='SET updated_at = :old',
        ExpressionAttributeValues={':old': {'S': old_time}}
    )
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    
    reap_stale_processing(table_name, resp['Item'])
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'STALE_PROCESSING'

@mock_aws
def test_reap_stale_pending_404():
    os.environ['REGION'] = 'us-east-1'
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    table_name = 'test_scans'
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    scan_id = create_pending_record(table_name, 'test.jpg', 'image/jpeg')
    
    # artificially age the record
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat().replace('+00:00', 'Z')
    dynamodb.update_item(
        TableName=table_name,
        Key={'scan_id': {'S': scan_id}},
        UpdateExpression='SET created_at = :old',
        ExpressionAttributeValues={':old': {'S': old_time}}
    )
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    
    reap_stale_pending(table_name, resp['Item'], 'test-bucket')
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'UPLOAD_TIMEOUT'

@mock_aws
def test_reap_stale_pending_exists():
    os.environ['REGION'] = 'us-east-1'
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    table_name = 'test_scans'
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    s3 = boto3.client('s3', region_name='us-east-1')
    s3.create_bucket(Bucket='test-bucket')
    
    scan_id = create_pending_record(table_name, 'test.jpg', 'image/jpeg')
    s3.put_object(Bucket='test-bucket', Key=f'uploads/{scan_id}.jpg', Body=b'dummy')
    
    # artificially age the record
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat().replace('+00:00', 'Z')
    dynamodb.update_item(
        TableName=table_name,
        Key={'scan_id': {'S': scan_id}},
        UpdateExpression='SET created_at = :old',
        ExpressionAttributeValues={':old': {'S': old_time}}
    )
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    
    reap_stale_pending(table_name, resp['Item'], 'test-bucket')
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'FAILED'
    assert resp['Item']['error']['M']['code']['S'] == 'EVENT_NOT_RECEIVED'
