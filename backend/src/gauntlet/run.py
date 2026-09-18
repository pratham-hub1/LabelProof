from src.gauntlet.cache import get_extraction_cache, put_extraction_cache
from src.gauntlet.word_index import build_word_index
from src.gauntlet.readability import compute_readability, load_readability_config
from src.gauntlet.anchors_loader import load_anchors_config
from src.gauntlet.mapper import map_field_result

def validate_schema(extraction):
    """
    Validates that the extraction is valid JSON matching the schema.
    Returns True if valid, False otherwise.
    """
    if not isinstance(extraction, dict):
        return False
    if extraction.get("schema_version") != "1.0":
        return False
    if "fields" not in extraction:
        return False
    return True

def run_gauntlet(image_bytes, content_type, bucket_name, etag, bedrock_caller, s3_client=None):
    """
    Main gauntlet orchestrator.
    Returns a dict containing:
    {
      "extraction": the extraction JSON,
      "gauntlet_results": dict of field -> {"gauntlet_status": ..., "reason_code": ...},
      "readability": bool,
      "error": str (if G0 fails)
    }
    """
    # 1. Cache
    extraction = get_extraction_cache(bucket_name, etag, s3_client=s3_client)
    
    if not extraction:
        # 2. Bedrock caller
        extraction = bedrock_caller(image_bytes, content_type)
        
        # Validate schema (G0)
        if not validate_schema(extraction):
            return {"error": "G0_SCHEMA_INVALID"}
            
        put_extraction_cache(bucket_name, etag, extraction, s3_client=s3_client)
        
    # 3. Word index
    word_index = build_word_index(image_bytes, content_type=content_type)
    
    # 4. Readability
    readability_config = load_readability_config()
    is_readable = compute_readability(word_index, readability_config)
    
    # 5. Gates & Mapper
    anchors_config = load_anchors_config()
    gauntlet_results = {}
    
    fields_to_check = [
        "manufacturer_name",
        "manufacturer_address",
        "generic_name",
        "net_quantity",
        "mrp",
        "mfg_date",
        "consumer_care"
    ]
    
    image_meta = extraction.get("image")
    
    for field in fields_to_check:
        claim = extraction["fields"].get(field)
        res = map_field_result(field, claim, word_index, is_readable, anchors_config, image_meta)
        gauntlet_results[field] = res
        
    return {
        "extraction": extraction,
        "gauntlet_results": gauntlet_results,
        "readability": is_readable,
        "word_index": word_index
    }
