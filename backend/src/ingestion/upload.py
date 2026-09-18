import json
import random
import os
import boto3
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Load config
CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'ingestion.config')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

CHARSET = CONFIG['scan_id_charset']

def generate_scan_id() -> str:
    chars = ''.join(random.choices(CHARSET, k=6))
    return f"SC-{chars}"

def create_pending_record(table_name: str, filename: str, content_type: str, label_width_mm: float = None) -> str:
    """
    Creates a PENDING record in DynamoDB with a unique scan_id.
    Retries up to 3 times on ID collision.
    """
    dynamodb = boto3.client('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    
    source_type = 'pdf' if content_type == 'application/pdf' else 'photo'
    ext = 'pdf' if source_type == 'pdf' else ('png' if content_type == 'image/png' else 'jpg')
    
    for _ in range(3):
        scan_id = generate_scan_id()
        now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
        s3_key = f"uploads/{scan_id}.{ext}"
        
        item = {
            'scan_id': {'S': scan_id},
            'status': {'S': 'PENDING'},
            'created_at': {'S': now},
            'updated_at': {'S': now},
            'input': {'M': {
                'filename': {'S': filename},
                'content_type': {'S': content_type},
                'source_type': {'S': source_type},
                's3_key': {'S': s3_key},
                'size_bytes': {'NULL': True}
            }},
            'product': {'NULL': True},
            'summary': {'NULL': True},
            'results': {'NULL': True},
            'error': {'NULL': True}
        }
        
        if label_width_mm is not None:
            item['input']['M']['label_width_mm'] = {'N': str(label_width_mm)}
        else:
            item['input']['M']['label_width_mm'] = {'NULL': True}

        try:
            dynamodb.put_item(
                TableName=table_name,
                Item=item,
                ConditionExpression='attribute_not_exists(scan_id)'
            )
            return scan_id
        except ClientError as e:
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                continue
            raise e
            
    raise RuntimeError("Failed to generate a unique scan_id after 3 attempts")
