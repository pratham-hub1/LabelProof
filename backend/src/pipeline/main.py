import os
import boto3
from PIL import Image
import io
import hashlib
from src.pipeline.artifacts import generate_and_upload_artifacts

def run_pipeline(scan_id: str, bucket_name: str, object_key: str, size_bytes: int, scan_fields: dict) -> dict:
    """
    Main pipeline orchestrator.
    Downloads the object, runs gauntlet/checks, generates artifacts, uploads them.
    """
    s3 = boto3.client('s3', region_name=os.environ.get('REGION', 'ap-south-1'))
    resp = s3.get_object(Bucket=bucket_name, Key=object_key)
    image_bytes = resp['Body'].read()
    
    # 1. Preprocess
    from src.preprocess.canonical import preprocess
    content_type = scan_fields.get('input', {}).get('content_type', 'image/jpeg')
    canonical_image = preprocess(image_bytes, content_type)
    
    # Convert canonical_image (PIL) to bytes for gauntlet/Bedrock/OCR
    buf = io.BytesIO()
    canonical_image.save(buf, format='JPEG', quality=95)
    canonical_bytes = buf.getvalue()
    
    # 2. Gauntlet (Mocked LLM extraction)
    from src.gauntlet.run import run_gauntlet
    
    def mock_bedrock_caller(img_bytes, ct):
        from src.extraction.client import extract
        def dummy_client(ibytes, prompt, model_id, schema):
            return {
                "schema_version": "1.0",
                "source_type": "photo",
                "image": {"width": 100, "height": 100},
                "language": "en",
                "fields": {
                    "manufacturer_name": {"raw": "Test Co", "parsed": {"name": "Test Co"}, "confidence": 0.9, "box": [0,0,1,1]},
                    "manufacturer_address": {"raw": "123 Test St", "parsed": {}, "confidence": 0.9, "box": [0,0,1,1]},
                    "generic_name": {"raw": None, "parsed": None, "confidence": None, "box": None},
                    "net_quantity": {"raw": None, "parsed": None, "confidence": None, "box": None},
                    "mfg_date": {"raw": None, "parsed": None, "confidence": None, "box": None},
                    "mrp": {"raw": None, "parsed": None, "confidence": None, "box": None},
                    "consumer_care": {"raw": None, "parsed": None, "confidence": None, "box": None}
                }
            }
        return extract(img_bytes, {}, model_client=dummy_client)
        
    etag = hashlib.md5(canonical_bytes).hexdigest()
    gauntlet_res = run_gauntlet(canonical_bytes, content_type, bucket_name, etag, mock_bedrock_caller)
    
    if "error" in gauntlet_res:
        return {
            'status': 'FAILED',
            'error_code': gauntlet_res["error"],
            'error_msg': "Gauntlet failed"
        }
        
    extraction = gauntlet_res["extraction"]
    field_status = gauntlet_res["gauntlet_results"]
    is_readable = gauntlet_res["readability"]
    word_index = gauntlet_res.get("word_index", [])
    
    # Exemption
    from src.rules.exemptions import evaluate_exemptions
    import json
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'tobacco.config'), 'r') as f:
        tobacco_config = json.load(f)
    exemption = evaluate_exemptions(field_status, tobacco_config)
    
    # Rules
    from src.rules.engine import run_checks
    context = {
        "extraction": extraction,
        "word_index": word_index,
        "field_status": {k: v.get("gauntlet_status") for k, v in field_status.items()},
        "readability": is_readable,
        "config": {}
    }
    results = run_checks(context)
    
    # Artifact generation
    outputs_bucket = os.environ.get('OUTPUTS_BUCKET', 'labelcheck-outputs')
    summary, artifacts = generate_and_upload_artifacts(
        scan_id=scan_id,
        canonical_image=canonical_image,
        scan_fields=scan_fields,
        results=results,
        exemption=exemption,
        field_status=field_status,
        outputs_bucket=outputs_bucket
    )
    
    return {
        'status': 'DONE' if summary.get('fail', 0) == 0 else 'NEEDS_REVIEW', 
        'summary': summary,
        'results': results,
        'artifacts': artifacts,
        'exemption': exemption,
        'extraction': extraction,
        'product': {}
    }
