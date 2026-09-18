import os
import boto3
import json
from src.api.serialize import serialize
from src.api.utils import _error
from src.ingestion.reapers import reap_stale_processing

def get_scan(scan_id: str) -> dict:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    # 1. Consistent Read
    response = table.get_item(
        Key={'scan_id': scan_id},
        ConsistentRead=True
    )
    item = response.get('Item')
    
    if not item:
        return _error(404, 'NOT_FOUND', f'Scan {scan_id} not found')
        
    # 2. Reaper Guard
    # If PENDING or PROCESSING, check staleness.
    # The F5 tests say "STALE_PROCESSING -> marks terminal as FAILED". 
    # Let's call reap_stale_processing for PROCESSING records.
    # We could also call reap_stale_pending for PENDING.
    status = item.get('status')
    if status == 'PROCESSING':
        # returns True if it was reaped
        if reap_stale_processing(table.name, item):
            # Fetch again since it was mutated
            response = table.get_item(Key={'scan_id': scan_id}, ConsistentRead=True)
            item = response.get('Item')
    elif status == 'PENDING':
        from src.ingestion.reapers import reap_stale_pending
        if reap_stale_pending(table.name, item):
            response = table.get_item(Key={'scan_id': scan_id}, ConsistentRead=True)
            item = response.get('Item')
            
    return {
        'statusCode': 200,
        'body': json.dumps(serialize(item))
    }
