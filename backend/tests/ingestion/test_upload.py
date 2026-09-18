import pytest
import os
import boto3
from moto import mock_aws
from src.ingestion.upload import generate_scan_id, create_pending_record
import re

@mock_aws
def test_generate_scan_id():
    scan_id = generate_scan_id()
    assert re.match(r'^SC-[A-HJ-NP-Z2-9]{6}$', scan_id)

@mock_aws
def test_create_pending_record():
    os.environ['REGION'] = 'us-east-1'
    dynamodb = boto3.client('dynamodb', region_name='us-east-1')
    table_name = 'test_scans'
    dynamodb.create_table(
        TableName=table_name,
        KeySchema=[{'AttributeName': 'scan_id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'scan_id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )
    
    scan_id = create_pending_record(table_name, 'test.jpg', 'image/jpeg', 90.0)
    
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    item = resp['Item']
    assert item['status']['S'] == 'PENDING'
    assert item['input']['M']['filename']['S'] == 'test.jpg'
    assert item['input']['M']['label_width_mm']['N'] == '90.0'
    assert item['input']['M']['content_type']['S'] == 'image/jpeg'
    assert item['input']['M']['source_type']['S'] == 'photo'
    assert item['input']['M']['s3_key']['S'] == f"uploads/{scan_id}.jpg"
