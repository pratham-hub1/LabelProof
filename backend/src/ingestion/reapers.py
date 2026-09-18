import boto3
import os
import json
from datetime import datetime, timezone
import dateutil.parser
from botocore.exceptions import ClientError
import logging
from src.ingestion.terminal import mark_terminal

logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ingestion.config')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

def reap_stale_processing(table_name: str, item: dict):
    """
    Checks if a PROCESSING item is stale (> 5 minutes).
    If so, transitions to FAILED(STALE_PROCESSING).
    """
    scan_id = item['scan_id']
    if isinstance(scan_id, dict):
        scan_id = scan_id['S']
        
    updated_at = item['updated_at']
    if isinstance(updated_at, dict):
        updated_at = updated_at['S']
    updated_at = dateutil.parser.isoparse(updated_at)
    
    now = datetime.now(timezone.utc)
    delta = (now - updated_at).total_seconds()
    
    if delta > CONFIG['stale_processing_seconds']:
        logger.warning(f"Scan {scan_id} is STALE_PROCESSING. Reaping.")
        mark_terminal(
            table_name=table_name,
            scan_id=scan_id,
            status='FAILED',
            error_code='STALE_PROCESSING',
            error_msg='Pipeline timed out during processing'
        )
        return True
    return False

def reap_stale_pending(table_name: str, item: dict, bucket_name: str):
    """
    Checks if a PENDING item is stale (> 960 seconds).
    If so, does a HeadObject. If 404, transitions to FAILED(UPLOAD_TIMEOUT).
    """
    scan_id = item['scan_id']
    if isinstance(scan_id, dict):
        scan_id = scan_id['S']
        
    created_at = item['created_at']
    if isinstance(created_at, dict):
        created_at = created_at['S']
    created_at = dateutil.parser.isoparse(created_at)
    
    now = datetime.now(timezone.utc)
    delta = (now - created_at).total_seconds()
    
    if delta > CONFIG['upload_timeout_seconds']:
        # Check S3
        s3 = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-south-1'))
        s3_key = item['input']['M']['s3_key']['S']
        
        try:
            s3.head_object(Bucket=bucket_name, Key=s3_key)
            # If it exists, maybe event was lost? F5 says EVENT_NOT_RECEIVED
            logger.warning(f"Scan {scan_id} PENDING but object exists. EVENT_NOT_RECEIVED.")
            mark_terminal(
                table_name=table_name,
                scan_id=scan_id,
                status='FAILED',
                error_code='EVENT_NOT_RECEIVED',
                error_msg='File uploaded but event trigger lost',
                from_pending=True
            )
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                logger.warning(f"Scan {scan_id} PENDING and object missing. UPLOAD_TIMEOUT.")
                mark_terminal(
                    table_name=table_name,
                    scan_id=scan_id,
                    status='FAILED',
                    error_code='UPLOAD_TIMEOUT',
                    error_msg='Upload did not complete within the window',
                    from_pending=True
                )
                return True
            else:
                raise e
        return True
    return False
