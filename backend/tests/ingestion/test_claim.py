import pytest
import os
import boto3
from moto import mock_aws
from src.ingestion.claim import claim_scan, parse_scan_id_from_key
from src.ingestion.upload import create_pending_record

@mock_aws
def test_claim_scan():
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
    
    # Successful claim
    claimed, _ = claim_scan(table_name, scan_id, 1024)
    assert claimed == True
    
    # Check if size was updated
    resp = dynamodb.get_item(TableName=table_name, Key={'scan_id': {'S': scan_id}})
    assert resp['Item']['status']['S'] == 'PROCESSING'
    assert resp['Item']['input']['M']['size_bytes']['N'] == '1024'
    
    # Duplicate claim should return False, not raise
    claimed, _ = claim_scan(table_name, scan_id, 1024)
    assert claimed == False

def test_parse_scan_id():
    assert parse_scan_id_from_key('uploads/SC-ABCDEF.jpg') == 'SC-ABCDEF'
