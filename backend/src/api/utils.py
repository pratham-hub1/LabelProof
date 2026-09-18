import json

def _error(status: int, code: str, msg: str) -> dict:
    return {
        'statusCode': status,
        'body': json.dumps({'error': {'code': code, 'message': msg}})
    }
