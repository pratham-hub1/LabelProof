import os
import boto3
from src.api.utils import _error

def redirect_report(scan_id: str, fmt: str) -> dict:
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    resp = table.get_item(
        Key={'scan_id': scan_id},
        ProjectionExpression='#st, artifacts',
        ExpressionAttributeNames={'#st': 'status'}
    )
    item = resp.get('Item')
    
    if not item:
        return _error(404, 'NOT_FOUND', f'Scan {scan_id} not found')
        
    status = item.get('status')
    if status in ('PENDING', 'PROCESSING'):
        return _error(404, 'NOT_FOUND', f'Scan {scan_id} hasn\'t finished')
        
    if status == 'FAILED' or not item.get('artifacts'):
        return _error(404, 'NOT_FOUND', f'No artifacts available for {scan_id}')
        
    # Maps requested fmt (pdf, csv, json, annotated, display) to internal keys
    # from T6 generation
    fmt_map = {
        'pdf': 'report_pdf',
        'csv': 'report_csv',
        'json': 'report_json',
        'annotated': 'annotated_image',
        'display': 'display_image'
    }
    
    if fmt not in fmt_map:
        return _error(400, 'BAD_REQUEST', f'Unknown format {fmt}')
        
    art_key = fmt_map[fmt]
    s3_key = item['artifacts'].get(art_key)
    
    if not s3_key:
        return _error(404, 'NOT_FOUND', f'Artifact {fmt} not found')
        
    # The artifact stores the literal S3 key, e.g. "outputs/reports/SC-123/report.pdf"
    # Convert to public HTTP URL. F7 says "Location: <public S3 URL>"
    bucket = os.environ.get('OUTPUTS_BUCKET', 'labelcheck-outputs')
    region = os.environ.get('REGION', 'ap-south-1')
    url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    
    return {
        'statusCode': 302,
        'headers': {
            'Location': url
        },
        'body': ''
    }
