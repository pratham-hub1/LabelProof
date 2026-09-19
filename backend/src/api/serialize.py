import re
import base64
import json

def normalize_key(s: str) -> str:
    """
    Lowercase and punctuation strip. Used at write AND query time.
    """
    if not s:
        return ""
    # strip anything that is not alphanumeric or space, then lower, then replace multiple spaces with single space
    s = re.sub(r'[^\w\s]', '', str(s))
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()

import decimal

def normalize_scalars(obj):
    if isinstance(obj, list):
        return [normalize_scalars(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: normalize_scalars(v) for k, v in obj.items()}
    elif isinstance(obj, decimal.Decimal):
        if obj % 1 == 0:
            return int(obj)
        return float(obj)
    else:
        return obj

def serialize(record: dict) -> dict:
    """
    Whitelist serializer emitting the contract shape only.
    internal keys (gsi1_pk, gsi1_sk, gsi2_pk, gsi2_sk, brand_key, product_key, failed_rules) never appear.
    """
    whitelist = {
        'scan_id', 'status', 'created_at', 'updated_at', 
        'input', 'product', 'extraction', 'summary', 
        'results', 'artifacts', 'exemption', 'error'
    }
    
    out = {}
    for k in whitelist:
        if k in record:
            out[k] = normalize_scalars(record[k])
    return out

def encode_cursor(key: dict) -> str:
    if not key:
        return None
    try:
        return base64.urlsafe_b64encode(json.dumps(key).encode('utf-8')).decode('utf-8')
    except Exception:
        return None

def decode_cursor(cursor: str) -> dict:
    if not cursor:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(cursor).decode('utf-8'))
    except Exception:
        raise ValueError("Invalid cursor format")
