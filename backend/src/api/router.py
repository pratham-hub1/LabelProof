import json
import logging
from src.api.utils import _error
from src.api.list_scans import list_scans
from src.api.search import search_scans
from src.api.get_scan import get_scan
from src.api.stats import get_stats
from src.api.reports import redirect_report

logger = logging.getLogger(__name__)

def route_api(event, context):
    """
    Main API router. Called from the lambda handler for GET /scans, etc.
    """
    method = event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    path = event.get('requestContext', {}).get('http', {}).get('path', '/')
    
    # trailing slash strip
    if path != '/' and path.endswith('/'):
        path = path.rstrip('/')
        
    query_params = event.get('queryStringParameters') or {}
    path_params = event.get('pathParameters') or {}

    logger.info(f"API Route: {method} {path} | params: {query_params}")

    if path == '/scans':
        if method != 'GET':
            return _error(405, 'METHOD_NOT_ALLOWED', 'Use GET')
        if 'query' in query_params:
            return search_scans(query_params)
        else:
            return list_scans(query_params)
            
    if path.startswith('/scans/'):
        if method != 'GET':
            return _error(405, 'METHOD_NOT_ALLOWED', 'Use GET')
        scan_id = path.split('/')[2]
        return get_scan(scan_id)
        
    if path == '/stats':
        if method != 'GET':
            return _error(405, 'METHOD_NOT_ALLOWED', 'Use GET')
        return get_stats()
        
    if path.startswith('/reports/'):
        if method != 'GET':
            return _error(405, 'METHOD_NOT_ALLOWED', 'Use GET')
        # e.g. /reports/SC-123.pdf
        filename = path.split('/')[2]
        if '.' not in filename:
            return _error(400, 'BAD_REQUEST', 'Missing format extension')
        scan_id, fmt = filename.split('.', 1)
        return redirect_report(scan_id, fmt)
        
    return _error(404, 'NOT_FOUND', 'Path not found')
