import io
import os
import boto3
import json
import logging
import time
from botocore.exceptions import ClientError
from PIL import Image

from src.reports.annotate import render_annotated
from src.reports.display import render_display_image
from src.reports.pdf import build_pdf_report
from src.reports.csv import build_csv_report, build_json_report
from src.reports.summary import compute_summary_counts, compute_found_declarations

logger = logging.getLogger(__name__)

def get_reports_config():
    config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'reports.config')
    with open(config_path, 'r') as f:
        return json.load(f)

def generate_and_upload_artifacts(
    scan_id: str, 
    canonical_image: Image.Image, 
    scan_fields: dict, 
    results: dict, 
    exemption: dict,
    field_status: dict,
    outputs_bucket: str
) -> tuple[dict, dict]:
    """
    Generates all 5 artifacts in memory and PUTs them to the outputs bucket.
    Returns (summary, artifacts_dict).
    Raises Exception if upload fails after retry.
    """
    config = get_reports_config()
    
    # 1. Compute summary counts
    found_declarations = compute_found_declarations(field_status)
    summary = compute_summary_counts(results, exemption.get('applied', False))
    summary['found_declarations'] = found_declarations
    
    # 2. Generate artifacts in memory
    # Annotated Image
    annotated_img = render_annotated(canonical_image, results, exemption, summary, config)
    annotated_io = io.BytesIO()
    # JPEG fixed quality 85, EXIF stripped (PIL save without exif strips it)
    annotated_img.save(annotated_io, format='JPEG', quality=config.get('jpeg_quality', 85))
    annotated_bytes = annotated_io.getvalue()
    
    # Display Image
    display_img = render_display_image(canonical_image, config)
    display_io = io.BytesIO()
    display_img.save(display_io, format='JPEG', quality=config.get('jpeg_quality', 85))
    display_bytes = display_io.getvalue()
    
    # PDF
    pdf_bytes = build_pdf_report(scan_fields, results, exemption, found_declarations, config, annotated_bytes)
    
    # CSV
    csv_bytes = build_csv_report(results, summary)
    
    # JSON
    # For JSON we need the full terminal record shape, but we don't have it fully yet 
    # since terminal mark is what writes to dynamodb. We'll build the record shape:
    record = scan_fields.copy()
    record['scan_id'] = scan_id
    record['results'] = results
    record['exemption'] = exemption
    record['summary'] = summary
    json_bytes = build_json_report(record)
    
    # 3. Upload to S3 (5 PUTs)
    s3 = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-south-1'))
    
    uploads = [
        (f"reports/{scan_id}/annotated.jpg", annotated_bytes, "image/jpeg"),
        (f"reports/{scan_id}/display.jpg", display_bytes, "image/jpeg"),
        (f"reports/{scan_id}/report.pdf", pdf_bytes, "application/pdf"),
        (f"reports/{scan_id}/data.csv", csv_bytes, "text/csv"),
        (f"reports/{scan_id}/record.json", json_bytes, "application/json")
    ]
    
    artifacts = {}
    
    retry_count = config.get('retry_count', 1)
    backoff = config.get('retry_backoff_seconds', 2)
    
    for key, data_bytes, content_type in uploads:
        success = False
        for attempt in range(retry_count + 1):
            try:
                s3.put_object(
                    Bucket=outputs_bucket,
                    Key=key,
                    Body=data_bytes,
                    ContentType=content_type
                )
                success = True
                break
            except ClientError as e:
                logger.warning(f"S3 PUT failed for {key} (attempt {attempt+1}): {e}")
                if attempt < retry_count:
                    time.sleep(backoff)
                    
        if not success:
            raise Exception(f"Failed to upload artifact {key} after {retry_count} retries")
            
        artifacts[key.split('/')[-1].split('.')[0]] = f"s3://{outputs_bucket}/{key}"
        
    return summary, artifacts
