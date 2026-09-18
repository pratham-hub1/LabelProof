import json
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables:
# TABLE_NAME, UPLOADS_BUCKET, OUTPUTS_BUCKET, WEB_BUCKET, AWS_REGION

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Check if this is an API Gateway / Function URL invocation
    if 'requestContext' in event and 'http' in event['requestContext']:
        method = event['requestContext']['http']['method']
        path = event['requestContext']['http']['path']
        logger.info(f"Function URL invocation: {method} {path}")
        
        # Route: POST /upload
        if path == '/upload' and method == 'POST':
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'upload stub'})
            }
            
        return {
            'statusCode': 404,
            'body': json.dumps({'error': {'code': 'NOT_FOUND', 'message': 'Path not found'}})
        }
        
    # Check if this is an S3 event invocation
    if 'Records' in event and len(event['Records']) > 0 and 's3' in event['Records'][0]:
        s3_event = event['Records'][0]
        bucket_name = s3_event['s3']['bucket']['name']
        object_key = s3_event['s3']['object']['key']
        
        logger.info(f"S3 event invocation: Bucket={bucket_name}, Key={object_key}")
        # Processing stub
        return {'status': 'success'}
        
    logger.warning("Unknown event type")
    return {'status': 'unknown_event'}
