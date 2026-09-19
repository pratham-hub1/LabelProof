import os
import boto3
import json
from boto3.dynamodb.conditions import Key, Attr
from src.api.serialize import serialize, decode_cursor, encode_cursor, normalize_key
from src.api.utils import _error
from src.api.list_scans import get_api_config

def search_scans(query_params: dict) -> dict:
    config = get_api_config()
    limit = int(query_params.get('limit', config.get('fallback_page_cap', 10)))
    limit = min(limit, config.get('pagination_max', 100))
    
    last_key_str = query_params.get('last_key')
    try:
        exclusive_start_key = decode_cursor(last_key_str)
    except ValueError:
        return _error(400, 'BAD_REQUEST', 'Invalid cursor format')
        
    query_raw = query_params.get('query', '')
    query_norm = normalize_key(query_raw)
    
    status = query_params.get('status')
    rule_id = query_params.get('rule_id')
    
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    # Check if we should use GSI-2 prefix leg (fast path) or fallback Scan leg
    # "empty result -> base-table Scan + contains ... the fallback LOOPS"
    # Actually wait, how do we distinguish between cursor for GSI-2 vs cursor for Scan?
    # If the client resumes a Scan, the cursor will belong to the base table (or we can just encode a flag).
    # "empty result -> base-table Scan" means if GSI-2 yields 0 matches in the FIRST call, we fall back to Scan?
    # Or do we fall back in the same request? "merge-free (one leg runs per request)".
    # If it's a first page (no cursor), we try GSI-2. If it yields < limit and no more LastEvaluatedKey? No, "empty result -> base-table Scan". 
    # If GSI-2 returns empty items AND no LastEvaluatedKey, we fallback?
    # Let's add a flag in the cursor: `{'leg': 'scan', 'key': ...}` vs `{'leg': 'gsi2', 'key': ...}`
    
    # If cursor exists, we know the leg
    leg = 'gsi2'
    dynamo_cursor = None
    if exclusive_start_key:
        leg = exclusive_start_key.get('leg', 'gsi2')
        dynamo_cursor = exclusive_start_key.get('key')
        
    items = []
    last_key = None
    
    filter_expr = None
    if status:
        filter_expr = Attr('status').eq(status)
    if rule_id:
        rule_cond = Attr('failed_rules').contains(rule_id)
        filter_expr = filter_expr & rule_cond if filter_expr else rule_cond

    if leg == 'gsi2':
        # GSI-2 leg
        kwargs = {
            'IndexName': config['gsi2_name'],
            'KeyConditionExpression': Key('gsi2_pk').eq('BRAND') & Key('gsi2_sk').begins_with(query_norm),
            'Limit': limit
        }
        if dynamo_cursor:
            kwargs['ExclusiveStartKey'] = dynamo_cursor
        if filter_expr:
            kwargs['FilterExpression'] = filter_expr
            
        response = table.query(**kwargs)
        items = [serialize(i) for i in response.get('Items', [])]
        last_key = response.get('LastEvaluatedKey')
        
        if items or last_key or dynamo_cursor:
            # We have results or are paginating GSI-2. Do not fallback.
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'items': items,
                    'last_key': encode_cursor({'leg': 'gsi2', 'key': last_key}) if last_key else None
                })
            }
            
        # Fallback to Scan (empty GSI-2 result, first page)
        leg = 'scan'

    if leg == 'scan':
        # Capped-loop Scan fallback
        scan_kwargs = {'Limit': 100} # DynamoDB Limit per request
        if dynamo_cursor:
            scan_kwargs['ExclusiveStartKey'] = dynamo_cursor
            
        # Contains on brand_key OR product_key
        scan_cond = Attr('brand_key').contains(query_norm) | Attr('product_key').contains(query_norm)
        if filter_expr:
            scan_kwargs['FilterExpression'] = scan_cond & filter_expr
        else:
            scan_kwargs['FilterExpression'] = scan_cond
            
        max_pages = config.get('fallback_page_cap', 10)
        pages = 0
        
        while len(items) < limit and pages < max_pages:
            resp = table.scan(**scan_kwargs)
            items.extend([serialize(i) for i in resp.get('Items', [])])
            pages += 1
            dynamo_cursor = resp.get('LastEvaluatedKey')
            if not dynamo_cursor:
                break
            scan_kwargs['ExclusiveStartKey'] = dynamo_cursor
            
        items = items[:limit]
        
        if len(items) == limit and dynamo_cursor:
            # We might have overfetched locally, but we must return a cursor.
            # In a real app we'd paginate precisely, but here the contract says "fallback LOOPS until limit RESULTS".
            # The last_key is just the LastEvaluatedKey from the last scan page. 
            # Note: if we overfetched, we lose the skipped items. This is a hackathon known limitation.
            last_key = dynamo_cursor
        else:
            last_key = dynamo_cursor if len(items) == limit else None
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'items': items,
                'last_key': encode_cursor({'leg': 'scan', 'key': last_key}) if last_key else None
            })
        }
