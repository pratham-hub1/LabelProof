import os
import boto3
import json
import time

_stats_cache = {}

def get_stats() -> dict:
    global _stats_cache
    
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            from decimal import Decimal
            if isinstance(obj, Decimal):
                return int(obj) if obj % 1 == 0 else float(obj)
            return super().default(obj)
            
    # Check cache (60s TTL)
    now = time.time()
    if 'data' in _stats_cache and 'ts' in _stats_cache:
        if now - _stats_cache['ts'] < 60:
            return {
                'statusCode': 200,
                'body': json.dumps(_stats_cache['data'], cls=DecimalEncoder)
            }
            
    dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-south-1'))
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    total_scans = 0
    overall = {'pass': 0, 'fail': 0, 'na': 0, 'needs_review': 0, 'exempt': 0}
    by_rule = {}
    
    # Scan the whole table using ProjectionExpression
    kwargs = {
        'ProjectionExpression': '#st, summary, results, failed_rules',
        'ExpressionAttributeNames': {'#st': 'status'}
    }
    
    while True:
        resp = table.scan(**kwargs)
        items = resp.get('Items', [])
        
        for item in items:
            total_scans += 1
            
            # terminal statuses with summary
            if item.get('status') in ('DONE', 'NEEDS_REVIEW') and 'summary' in item:
                summ = item['summary']
                overall['pass'] += summ.get('pass', 0)
                overall['fail'] += summ.get('fail', 0)
                overall['na'] += summ.get('na', 0)
                overall['needs_review'] += summ.get('needs_review', 0)
                overall['exempt'] += summ.get('exempt', 0)
                
            if item.get('results'):
                for rule_id, res in item['results'].items():
                    if rule_id not in by_rule:
                        by_rule[rule_id] = {'pass': 0, 'fail': 0, 'na': 0, 'needs_review': 0, 'exempt': 0}
                    st = res.get('status', 'NA').lower()
                    if st in by_rule[rule_id]:
                        by_rule[rule_id][st] += 1
                        
        cursor = resp.get('LastEvaluatedKey')
        if not cursor:
            break
        kwargs['ExclusiveStartKey'] = cursor
        
    # filter by_rule to >0 scans
    filtered_by_rule = {}
    rule_fail_counts = []
    
    for r_id, counts in by_rule.items():
        total_for_rule = sum(counts.values())
        if total_for_rule > 0:
            filtered_by_rule[r_id] = counts
            if counts['fail'] > 0:
                rule_fail_counts.append((r_id, counts['fail']))
                
    rule_fail_counts.sort(key=lambda x: x[1], reverse=True)
    most_failed_rules = [{"rule_id": r[0], "count": r[1]} for r in rule_fail_counts]
    
    data = {
        'total_scans': total_scans,
        'overall': overall,
        'by_rule': filtered_by_rule,
        'most_failed_rules': most_failed_rules
    }
    
    _stats_cache['data'] = data
    _stats_cache['ts'] = now
    
    return {
        'statusCode': 200,
        'body': json.dumps(data, cls=DecimalEncoder)
    }
