import boto3
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def claim_scan(table_name: str, scan_id: str, size_bytes: int) -> tuple[bool, dict]:
    """
    Performs the conditional update from PENDING to PROCESSING.
    Returns (True, item) if claimed, (False, {}) if the condition failed.
    Never raises on condition failure.
    """
    dynamodb = boto3.client('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    try:
        response = dynamodb.update_item(
            TableName=table_name,
            Key={'scan_id': {'S': scan_id}},
            UpdateExpression='SET #st = :processing, updated_at = :now, #inp.size_bytes = :size',
            ConditionExpression='#st = :pending',
            ExpressionAttributeNames={
                '#st': 'status',
                '#inp': 'input'
            },
            ExpressionAttributeValues={
                ':processing': {'S': 'PROCESSING'},
                ':pending': {'S': 'PENDING'},
                ':now': {'S': now},
                ':size': {'N': str(size_bytes)}
            },
            ReturnValues='ALL_NEW'
        )
        return True, response.get('Attributes', {})
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"Scan {scan_id} claim failed (condition).")
            return False, {}
        raise e
        
def parse_scan_id_from_key(key: str) -> str:
    """
    Parses scan_id from S3 key like 'uploads/SC-ABCDEF.jpg'.
    """
    basename = os.path.basename(key)
    scan_id = os.path.splitext(basename)[0]
    return scan_id
