import boto3
import os
import json
from datetime import datetime, timezone
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def mark_terminal(table_name: str, scan_id: str, status: str, error_code: str = None, error_msg: str = None, 
                  product: dict = None, extraction: dict = None, summary: dict = None, results: list = None, 
                  artifacts: dict = None, exemption: dict = None, from_pending: bool = False, created_at: str = None):
    """
    Conditional write guarded on status = PROCESSING (or PENDING if from_pending=True for upload timeouts).
    """
    dynamodb = boto3.client('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    expr_set = ['#st = :status', 'updated_at = :now']
    expr_names = {'#st': 'status'}
    expr_vals = {
        ':status': {'S': status},
        ':now': {'S': now},
        ':expected_status': {'S': 'PENDING' if from_pending else 'PROCESSING'}
    }
    
    if error_code:
        expr_set.append('#err = :err')
        expr_names['#err'] = 'error'
        expr_vals[':err'] = {'M': {'code': {'S': error_code}, 'message': {'S': error_msg or ''}}}
    else:
        expr_set.append('#err = :null_val')
        expr_names['#err'] = 'error'
    
    # helper for mapping json back to dynamodb format (we could use boto3.dynamodb.types.TypeSerializer, but simple here)
    # wait, it's easier to use the high-level Table resource for complex types, but we'll stick to client for determinism
    # Let's import TypeSerializer
    from boto3.dynamodb.types import TypeSerializer
    serializer = TypeSerializer()
    
    if product:
        expr_set.append('product = :prod')
        expr_vals[':prod'] = serializer.serialize(product)
    
    if extraction:
        expr_set.append('extraction = :ext')
        expr_vals[':ext'] = serializer.serialize(extraction)
        
    if summary:
        expr_set.append('summary = :sum')
        expr_vals[':sum'] = serializer.serialize(summary)
        
    if results is not None:
        expr_set.append('results = :res')
        expr_vals[':res'] = serializer.serialize(results)
        
    if artifacts:
        expr_set.append('artifacts = :art')
        expr_vals[':art'] = serializer.serialize(artifacts)
        
    if exemption:
        expr_set.append('exemption = :exm')
        expr_vals[':exm'] = serializer.serialize(exemption)
        
    if ':null_val' in expr_set[-1] or error_code is None: # ensure :null_val is defined if used
        expr_vals[':null_val'] = {'NULL': True}
        
    # F7 Search keys
    from src.api.serialize import normalize_key
    if product:
        if 'brand_guess' in product:
            brand_key = normalize_key(product['brand_guess'])
            if brand_key:
                expr_set.extend(['brand_key = :bk', 'gsi2_pk = :g2pk'])
                expr_vals[':bk'] = {'S': brand_key}
                expr_vals[':g2pk'] = {'S': 'BRAND'}
                if created_at:
                    expr_set.append('gsi2_sk = :g2sk')
                    expr_vals[':g2sk'] = {'S': f"{brand_key}#{created_at}#{scan_id}"}
        
        if 'product_name' in product:
            product_key = normalize_key(product['product_name'])
            if product_key:
                expr_set.append('product_key = :pk')
                expr_vals[':pk'] = {'S': product_key}
                
    if results:
        failed = [k for k, v in results.items() if v.get('status') == 'FAIL']
        if failed:
            expr_set.append('failed_rules = :fr')
            expr_vals[':fr'] = {'SS': failed}
    
    # if successful scan, we also write F7's GSI attributes here. (F5 doc says they are added here if we reached F7). 
    # But F7 says "All computed at the terminal write... F5's conditional-guard design is unchanged"
    # To keep it simple, I'll add them if product/results are present.
    # Actually wait, I should compute gsi keys!
    # gsi1_pk = "SCAN", gsi1_sk = created_at#scan_id
    # gsi2_pk = "BRAND", gsi2_sk = brand_key#created_at#scan_id
    # We need created_at to form the SK. We don't have it here unless we read it or pass it.
    # F7 says "every scan record carries at write time".
    # Wait, the GSI keys can be set in create_pending_record!
    
    update_expr = 'SET ' + ', '.join(expr_set)
    
    try:
        dynamodb.update_item(
            TableName=table_name,
            Key={'scan_id': {'S': scan_id}},
            UpdateExpression=update_expr,
            ConditionExpression='#st = :expected_status',
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_vals
        )
    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"Scan {scan_id} mark_terminal failed (condition).")
            return False
        raise e
        
    return True
