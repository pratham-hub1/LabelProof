import os
import boto3
import json
from boto3.dynamodb.conditions import Key, Attr
from src.api.serialize import serialize, decode_cursor, encode_cursor
from src.api.utils import _error

def get_api_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api.config')
    with open(config_path, 'r') as f:
        return json.load(f)

def list_scans(query_params: dict) -> dict:
    config = get_api_config()
    limit = int(query_params.get('limit', config.get('fallback_page_cap', 10)))
    limit = min(limit, config.get('pagination_max', 100))
    
    last_key_str = query_params.get('last_key')
    try:
        exclusive_start_key = decode_cursor(last_key_str)
    except ValueError:
        return _error(400, 'BAD_REQUEST', 'Invalid cursor format')
        
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    kwargs = {
        'IndexName': config['gsi1_name'],
        'KeyConditionExpression': Key('gsi1_pk').eq('SCAN'),
        'ScanIndexForward': False, # newest first
        'Limit': limit
    }
    if exclusive_start_key:
        kwargs['ExclusiveStartKey'] = exclusive_start_key
        
    filter_expr = None
    status = query_params.get('status')
    if status:
        filter_expr = Attr('status').eq(status)
        
    rule_id = query_params.get('rule_id')
    if rule_id:
        rule_cond = Attr('failed_rules').contains(rule_id)
        if filter_expr:
            filter_expr = filter_expr & rule_cond
        else:
            filter_expr = rule_cond
            
    if filter_expr:
        kwargs['FilterExpression'] = filter_expr
        
    response = table.query(**kwargs)
    items = [serialize(i) for i in response.get('Items', [])]
    next_key = response.get('LastEvaluatedKey')
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'items': items,
            'next_key': encode_cursor(next_key) if next_key else None
        })
    }
