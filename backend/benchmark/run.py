import os
import io
import json
import uuid
import datetime
import boto3
from unittest import mock
from moto import mock_aws
from PIL import Image, ImageDraw

from src.gauntlet.run import run_gauntlet
from src.geometry.calibrate import calibrate_photo
from src.geometry.thresholds_loader import load_thresholds_config
from src.rules.patterns_loader import load_patterns_config
from src.rules.exemptions import evaluate_exemptions
from src.rules.statuses import resolve_field_statuses
from src.rules.engine import run_checks
# Import checks to register them
import src.rules.checks.r1
import src.rules.checks.r2
import src.rules.checks.r3
import src.rules.checks.r4
import src.rules.checks.r5
import src.rules.checks.r6_r11
from src.rules.verdict import final_verdict


def mock_bedrock_caller(image_bytes, content_type):
    # Mock extraction based on synthetic image
    return {
        "schema_version": "1.0",
        "source_type": "photo",
        "image": {"width": 800, "height": 600},
        "language": "en",
        "fields": {
            "manufacturer_name": {"raw": "Test Corp", "confidence": 0.9},
            "manufacturer_address": {"raw": "123 Main St, Mumbai 400001, Maharashtra", "confidence": 0.9},
            "generic_name": {"raw": "Test Snack", "confidence": 0.9},
            "net_quantity": {"raw": "200 g", "parsed": {"value": 200, "unit": "g"}, "confidence": 0.9},
            "mrp": {"raw": "MRP Rs. 20 (inclusive of all taxes)", "parsed": {"value": 20, "currency": "INR"}, "confidence": 0.9},
            "mfg_date": {"raw": "MFG 08/2026", "parsed": {"month": 8, "year": 2026}, "confidence": 0.9},
            "consumer_care": {"raw": "care@test.com", "parsed": {"email": "care@test.com"}, "confidence": 0.9}
        }
    }

def offline_replay(record: dict) -> dict:
    """
    Offline replay: harvested extraction -> gauntlet -> rule engine -> results.
    Bypasses Bedrock and network completely.
    """
    skip_cache = os.environ.get('BENCHMARK_SKIP_CACHE', '0') == '1'
    if skip_cache:
        # In a real environment, this would call bedrock again.
        # But this is offline, so we'd raise or simulate network call.
        pass
        
    input_data = record.get('input', {})
    extraction = record.get('extraction', {})
    product_guess = record.get('product', {})
    exemption = record.get('exemption', {})
    
    # Run the pure rule engine (skip geometry since we don't have the image, rely on harvested data)
    field_status = record.get('field_status', {})
    if not field_status:
        # Gauntlet re-run
        from src.gauntlet.mapper import map_bedrock_to_checks
        from src.gauntlet.readability import check_readability
        gauntlet_results = map_bedrock_to_checks(extraction)
        is_readable = check_readability(extraction, gauntlet_results)
        import json; tobacco_config = json.load(open("backend/config/tobacco.config"))
        exemptions = evaluate_exemptions(extraction, tobacco_config)
        field_status = resolve_field_statuses(gauntlet_results, is_readable, exemptions)

    image_meta = record.get('_debug_image_meta', {}) 
    
    results, summary, overall_status = run_checks(
        extraction=extraction,
        field_status=field_status,
        product=product_guess,
        exemption=exemption,
        source_type=input_data.get('source_type', 'photo'),
        label_width_mm=input_data.get('label_width_mm'),
        image_meta=image_meta
    )
    
    return {
        'results': results,
        'summary': summary,
        'status': overall_status,
        'field_status': field_status
    }

def pipeline(image_bytes, label_width_mm, s3_client):
    # Fixed scan ID for determinism test
    scan_id = "test-scan-123"
    # Fixed timestamp for determinism test
    submitted_at = "2026-09-18T10:00:00Z"
    
    # 1. Gauntlet
    gauntlet = run_gauntlet(
        image_bytes=image_bytes,
        content_type="image/jpeg",
        bucket_name="test-bucket",
        etag="test-etag",
        bedrock_caller=mock_bedrock_caller,
        s3_client=s3_client
    )
    if "error" in gauntlet:
        return scan_id, {"verdict": "FAILED", "error": gauntlet["error"], "submitted_at": submitted_at}, b""
        
    extraction = gauntlet["extraction"]
    gauntlet_results = gauntlet["gauntlet_results"]
    is_readable = gauntlet["readability"]
    word_index = gauntlet.get("word_index", [])
    
    # 2. Calibrate (now with word_index)
    calib = calibrate_photo(image_bytes, label_width_mm, word_index)
    if "error" in calib:
        return scan_id, {"verdict": "FAILED", "error": calib["error"], "submitted_at": submitted_at}, b""
        
    scale = calib["scale"]
    sigma = calib["sigma"]
    pdp_area = calib["pdp_area_cm2"]
    
    # 3. Exemptions
    import json; tobacco_config = json.load(open("backend/config/tobacco.config")); exemptions = evaluate_exemptions(extraction, tobacco_config)
    
    # 4. Resolve Statuses
    field_status = resolve_field_statuses(gauntlet_results, is_readable, exemptions)
    
    # 5. Run Checks
    config = {
        **load_thresholds_config(),
        **load_patterns_config()
    }
    context = {
        "extraction": extraction,
        "word_index": [], # Not mocking full word index for pipeline benchmark
        "field_status": field_status,
        "readability": is_readable,
        "config": config,
        "image": image_bytes, # pass image
        "input": {"source_type": "photo", "label_width_mm": label_width_mm}
    }
    check_results = run_checks(context)
    
    # 6. Verdict
    verdict = final_verdict(field_status, check_results)
    
    # 7. PDF
    scan_fields = {
        "scan_id": scan_id,
        "created_at": submitted_at,
        "input": {"source_type": "photo", "label_width_mm": label_width_mm}
    }
    
    # Dummy annotated image for determinism test
    annotated_bytes = image_bytes 
    from src.reports.pdf import build_pdf_report
    pdf_bytes = build_pdf_report(scan_fields, list(check_results.values()), exemptions, 7, {}, annotated_bytes)
    
    record = {
        "scan_id": scan_id,
        "submitted_at": submitted_at,
        "verdict": verdict,
        "field_status": field_status,
        "check_results": check_results,
        "extraction": extraction
    }
    
    return scan_id, record, pdf_bytes

def create_synthetic_image():
    # 3000x2000 image, 2500x1250 rectangle inside (scale=25 for 100mm)
    img = Image.new('L', (3000, 2000), color=255)
    draw = ImageDraw.Draw(img)
    left = (3000 - 2500) // 2
    top = (2000 - 1250) // 2
    draw.rectangle([left, top, left + 2500 - 1, top + 1250 - 1], fill=100)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()

if __name__ == "__main__":
    print("Running pipeline determinism benchmark...")
    img = create_synthetic_image()
    
    with mock_aws():
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "ap-south-1"
        s3 = boto3.client("s3")
        s3.create_bucket(
            Bucket="test-bucket",
            CreateBucketConfiguration={'LocationConstraint': 'ap-south-1'}
        )
        
        # Run 1
        with mock.patch("src.gauntlet.run.build_word_index") as mock_build_word_index:
            mock_build_word_index.return_value = []
            scan_id1, record1, pdf1 = pipeline(img, 100.0, s3)
        # Run 2
        with mock.patch("src.gauntlet.run.build_word_index") as mock_build_word_index:
            mock_build_word_index.return_value = []
            scan_id2, record2, pdf2 = pipeline(img, 100.0, s3)
        
        assert pdf1 == pdf2, "PDFs are not identical across runs! Determinism failure."
        print("Determinism test PASSED. PDFs are identical.")
