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
    
    # 2. Gauntlet (Mocked or Live LLM extraction)
    from src.gauntlet.run import run_gauntlet
    
    use_mock = os.environ.get('USE_MOCK_BEDROCK', 'true').lower() == 'true'
    
    import json
    with open(os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'api.config'), 'r') as f:
        api_config = json.load(f)
    
    def bedrock_caller(img_bytes, ct):
        from src.extraction.client import extract
        if use_mock:
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
            return extract(img_bytes, api_config, model_client=dummy_client)
        else:
            return extract(img_bytes, api_config)
            
    etag = hashlib.md5(canonical_bytes).hexdigest()
    gauntlet_res = run_gauntlet(canonical_bytes, content_type, bucket_name, etag, bedrock_caller)
    
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
    raw_exemption = evaluate_exemptions(field_status, tobacco_config)
    
    # The new exemption dictionary shape has {applied, citation, reason, status_override}
    # We must format it to {applied, citation, reason} for persistence
    exemption = None
    if raw_exemption and raw_exemption.get("applied") is not None:
        exemption = {
            "applied": raw_exemption.get("applied"),
            "citation": raw_exemption.get("citation"),
            "reason": raw_exemption.get("reason")
        }
    
    # Resolve field statuses before run_checks
    from src.rules.statuses import resolve_field_statuses
    resolved_field_status = resolve_field_statuses(field_status, is_readable, raw_exemption)
    
    # Rules
    from src.rules.engine import run_checks
    context = {
        "extraction": extraction,
        "word_index": word_index,
        "field_status": resolved_field_status,
        "readability": is_readable,
        "config": {},
        "image": canonical_image,
        "scan_fields": scan_fields,
        "content_type": content_type
    }
    
    if raw_exemption and raw_exemption.get("status_override") == "EXEMPT":
        # Short-circuit all checks to NA_EXEMPT
        from src.rules.engine import registry
        results_dict = {}
        for rule_id in registry.checks.keys():
            results_dict[rule_id] = {"status": "NA", "reason_code": "NA_EXEMPT", "message": "Exempt package"}
    else:
        results_dict = run_checks(context)
        
    # Map to CONTRACTS array of exactly 11 objects
    results_array = []
    # Known mapping of rule_id to name and citation per DECISIONS.md
    rule_meta = {
        "r1_name_address": {"id": "R1", "name": "Manufacturer/packer/importer name + complete address", "citation": "Rule 6(1)(a), 10(1) — LMPC (PC) Rules, 2011"},
        "r2_generic_name": {"id": "R2", "name": "Common/generic name of commodity", "citation": "Rule 6(1)(b) — LMPC (PC) Rules, 2011"},
        "r3_net_quantity": {"id": "R3", "name": "Net quantity in correct unit", "citation": "Rule 6(1)(c), 13 — LMPC (PC) Rules, 2011"},
        "r4_mfg_date": {"id": "R4", "name": "Month & year of manufacture", "citation": "Rule 6(1)(d) — LMPC (PC) Rules, 2011"},
        "r5_mrp": {"id": "R5", "name": "MRP prescribed wording", "citation": "Rule 2(m), 6(1)(e) — LMPC (PC) Rules, 2011"},
        "r6_consumer_care": {"id": "R6", "name": "Consumer care details", "citation": "Rule 6(2) — LMPC (PC) Rules, 2011"},
        "r7_language": {"id": "R7", "name": "Declarations in Hindi (Devanagari) or English", "citation": "Rule 9(4) — LMPC (PC) Rules, 2011"},
        "r8_numeral_height": {"id": "R8", "name": "Minimum numeral height", "citation": "Rule 7(2), 7(3) — LMPC (PC) Rules, 2011"},
        "r9_clear_space": {"id": "R9", "name": "Clear space around the quantity declaration", "citation": "Rule 8 — LMPC (PC) Rules, 2011"},
        "r10_contrast": {"id": "R10", "name": "Contrast of MRP/quantity numerals", "citation": "Rule 9(1)(b) — LMPC (PC) Rules, 2011"},
        "r11_qualifiers": {"id": "R11", "name": "No misleading quantity qualifiers", "citation": "Rule 12(6) — LMPC (PC) Rules, 2011"}
    }
    
    for rule_key, meta in rule_meta.items():
        res = results_dict.get(rule_key, {"status": "NA", "reason_code": "NOT_PRINTED", "message": "Rule not executed"})
        
        evidence = res.get("message") or res.get("reason")
        
        item = {
            "rule_id": meta["id"],
            "name": meta["name"],
            "citation": meta["citation"],
            "status": res["status"],
            "evidence": evidence if evidence else None,
            "fix": res.get("fix", None),
            "box": res.get("box", None),
            "measurement": res.get("measurement", None)
        }
        results_array.append(item)
        
    assert len(results_array) == 11, "Validation failed: results array must contain exactly 11 items"
    
    # Artifact generation
    outputs_bucket = os.environ.get('OUTPUTS_BUCKET', 'labelcheck-outputs')
    summary, artifacts = generate_and_upload_artifacts(
        scan_id=scan_id,
        canonical_image=canonical_image,
        scan_fields=scan_fields,
        results=results_array,
        exemption=exemption or {},
        field_status=resolved_field_status,
        outputs_bucket=outputs_bucket
    )
    
    from src.rules.verdict import final_verdict
    # final_verdict takes field_statuses and check_results (as a dict mapping rule_id -> result)
    # We pass resolved_field_status and results_dict
    verdict = final_verdict(resolved_field_status, results_dict)
    
    if raw_exemption and raw_exemption.get("status_override") == "NEEDS_REVIEW" and verdict == "DONE":
        verdict = "NEEDS_REVIEW"
    
    return {
        'status': verdict,
        'summary': summary,
        'results': results_array,
        'artifacts': artifacts,
        'exemption': exemption,
        'extraction': extraction,
        'product': {}
    }
