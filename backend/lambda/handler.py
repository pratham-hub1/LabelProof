import json
import os
import logging
import boto3
from urllib.parse import unquote
from src.ingestion.upload import create_pending_record
from src.ingestion.presign import presign_upload
from src.ingestion.claim import claim_scan, parse_scan_id_from_key
from src.ingestion.terminal import mark_terminal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'config', 'ingestion.config')
with open(CONFIG_PATH, 'r') as f:
    CONFIG = json.load(f)

# Environment variables
TABLE_NAME = os.environ.get('TABLE_NAME')
UPLOADS_BUCKET = os.environ.get('UPLOADS_BUCKET')
OUTPUTS_BUCKET = os.environ.get('OUTPUTS_BUCKET')
WEB_BUCKET = os.environ.get('WEB_BUCKET')

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # 1. Function URL / API Gateway invocation
    if 'requestContext' in event and 'http' in event['requestContext']:
        method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']
        logger.info(f"Function URL invocation: {method} {path}")
        
        if path == '/upload' and method == 'POST':
            try:
                body = json.loads(event.get('body', '{}'))
                filename = body.get('filename')
                content_type = body.get('content_type')
                label_width_mm = body.get('label_width_mm')
                
                if not filename or not content_type:
                    return _error_response(400, 'BAD_REQUEST', 'Missing filename or content_type')
                
                if content_type not in CONFIG['allowed_content_types']:
                    return _error_response(400, 'BAD_REQUEST', f'Unsupported content_type. Allowed: {CONFIG["allowed_content_types"]}')
                    
                if label_width_mm is not None:
                    try:
                        label_width_mm = float(label_width_mm)
                        if label_width_mm <= 0:
                            raise ValueError()
                    except ValueError:
                        return _error_response(400, 'BAD_REQUEST', 'label_width_mm must be a positive number')
                
                # Create PENDING record
                scan_id = create_pending_record(
                    table_name=TABLE_NAME,
                    filename=filename,
                    content_type=content_type,
                    label_width_mm=label_width_mm
                )
                
                # Generate presigned URL
                source_type = 'pdf' if content_type == 'application/pdf' else 'photo'
                ext = 'pdf' if source_type == 'pdf' else ('png' if content_type == 'image/png' else 'jpg')
                s3_key = f"uploads/{scan_id}.{ext}"
                
                upload_url = presign_upload(
                    bucket=UPLOADS_BUCKET,
                    key=s3_key,
                    content_type=content_type
                )
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'scan_id': scan_id,
                        'upload_url': upload_url,
                        'expires_in': CONFIG['presign_expiry_seconds']
                    })
                }
                
            except json.JSONDecodeError:
                return _error_response(400, 'BAD_REQUEST', 'Invalid JSON body')
            except Exception as e:
                logger.error(f"Error processing upload: {e}")
                return _error_response(500, 'INTERNAL', 'Internal server error')
                
        if path != '/upload' or method != 'POST':
            from src.api.router import route_api
            return route_api(event, context)
        
    # 2. S3 Event invocation
    if 'Records' in event and len(event['Records']) > 0 and 's3' in event['Records'][0]:
        s3_event = event['Records'][0]
        bucket_name = s3_event['s3']['bucket']['name']
        object_key = unquote(s3_event['s3']['object']['key'])
        size_bytes = s3_event['s3']['object']['size']
        
        logger.info(f"S3 event invocation: Bucket={bucket_name}, Key={object_key}, Size={size_bytes}")
        
        scan_id = parse_scan_id_from_key(object_key)
        
        # Size gate
        if size_bytes > CONFIG['size_cap_bytes']:
            logger.warning(f"Scan {scan_id} failed size gate. Size {size_bytes} > {CONFIG['size_cap_bytes']}")
            mark_terminal(
                table_name=TABLE_NAME,
                scan_id=scan_id,
                status='FAILED',
                error_code='OVERSIZED_FILE',
                error_msg=f'File size {size_bytes} exceeds {CONFIG["size_cap_bytes"]} bytes',
                from_pending=True
            )
            return {'status': 'oversized'}
            
        # Claim
        claimed, record = claim_scan(
            table_name=TABLE_NAME,
            scan_id=scan_id,
            size_bytes=size_bytes
        )
        
        if not claimed:
            logger.info(f"Scan {scan_id} could not be claimed. Skipping.")
            return {'status': 'skipped'}
            
        # Pipeline Handoff
        try:
            from src.pipeline.main import run_pipeline
            
            # Extract scan_fields from the DynamoDB item format
            from boto3.dynamodb.types import TypeDeserializer
            deserializer = TypeDeserializer()
            scan_fields = {k: deserializer.deserialize(v) for k, v in record.items()}
            
            result = run_pipeline(scan_id, bucket_name, object_key, size_bytes, scan_fields)
            
            # mark terminal
            kwargs = {
                'table_name': TABLE_NAME,
                'scan_id': scan_id,
                'status': result['status'],
                'product': result.get('product'),
                'extraction': result.get('extraction'),
                'summary': result.get('summary'),
                'results': result.get('results'),
                'artifacts': result.get('artifacts'),
                'exemption': result.get('exemption'),
                'created_at': scan_fields.get('created_at')
            }
            if result['status'] == 'FAILED':
                kwargs['error_code'] = result.get('error_code', 'INTERNAL')
                kwargs['error_msg'] = result.get('error_msg', 'Pipeline failed')
                
            mark_terminal(**kwargs)
        except Exception as e:
            logger.error(f"Pipeline failed for {scan_id}: {e}")
            mark_terminal(
                table_name=TABLE_NAME,
                scan_id=scan_id,
                status='FAILED',
                error_code='INTERNAL',
                error_msg='Internal pipeline error'
            )
            # B2 Fix: FAILED status must never coexist with public artifacts
            # Cleanup any artifacts that might have been uploaded before the crash/DB failure
            s3_client = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-south-1'))
            outputs_bucket = os.environ.get('OUTPUTS_BUCKET', 'labelcheck-outputs')
            keys_to_delete = [
                f"outputs/reports/{scan_id}/annotated.jpg",
                f"outputs/reports/{scan_id}/display.jpg",
                f"outputs/reports/{scan_id}/report.pdf",
                f"outputs/reports/{scan_id}/data.csv",
                f"outputs/reports/{scan_id}/record.json"
            ]
            try:
                s3_client.delete_objects(
                    Bucket=outputs_bucket,
                    Delete={'Objects': [{'Key': k} for k in keys_to_delete], 'Quiet': True}
                )
            except Exception as del_err:
                logger.error(f"Failed to cleanup artifacts for {scan_id}: {del_err}")
            
        return {'status': 'success'}
        
    logger.warning("Unknown event type")
    return {'status': 'unknown_event'}

def _error_response(status_code: int, code: str, message: str) -> dict:
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': {'code': code, 'message': message}})
    }
