import os
import time
import requests
import json
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class BenchmarkCollector:
    def __init__(self, api_url: str):
        self.api_url = api_url.rstrip('/')
        
    def upload_label(self, filepath: str, source_type: str = 'photo', label_width_mm: float = None) -> str:
        """
        Uploads a label to the deployed API and returns the scan_id.
        """
        with open(filepath, 'rb') as f:
            content = f.read()
            
        filename = os.path.basename(filepath)
        content_type = 'application/pdf' if source_type == 'pdf' else 'image/jpeg'
        
        payload = {
            'filename': filename,
            'content_type': content_type
        }
        if label_width_mm:
            payload['label_width_mm'] = label_width_mm
            
        # 1. Get presigned URL
        res = requests.post(f"{self.api_url}/upload", json=payload)
        res.raise_for_status()
        data = res.json()
        
        scan_id = data['scan_id']
        upload_url = data['upload_url']
        
        # 2. Upload file directly to S3
        put_res = requests.put(upload_url, data=content, headers={'Content-Type': content_type})
        put_res.raise_for_status()
        
        return scan_id

    def poll_scan(self, scan_id: str, timeout_seconds: int = 60) -> Dict:
        """
        Polls the API until the scan reaches a terminal state.
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            res = requests.get(f"{self.api_url}/scans/{scan_id}")
            if res.status_code == 200:
                record = res.json()
                if record.get('status') not in ('PENDING', 'PROCESSING'):
                    return record
            time.sleep(2)
        raise TimeoutError(f"Scan {scan_id} did not complete within {timeout_seconds}s")
        
    def harvest(self, labels: List[Dict], directory: str) -> List[Dict]:
        """
        Uploads and polls a batch of labels, returning the harvested records.
        """
        harvested = []
        for label in labels:
            label_id = label['label_id']
            ext = 'pdf' if label.get('source_type') == 'pdf' else 'jpg'
            filepath = os.path.join(directory, f"{label_id}.{ext}")
            
            if not os.path.exists(filepath):
                logger.warning(f"File missing for {label_id}")
                continue
                
            width = label.get('measured_width_mm')
            scan_id = self.upload_label(filepath, label.get('source_type', 'photo'), width)
            logger.info(f"Uploaded {label_id} as {scan_id}")
            
            try:
                record = self.poll_scan(scan_id)
                harvested.append({
                    'label_id': label_id,
                    'scan_id': scan_id,
                    'record': record
                })
            except TimeoutError as e:
                logger.error(str(e))
                
        return harvested
