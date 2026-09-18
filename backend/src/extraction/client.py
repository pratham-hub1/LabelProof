import os
import json
from src.extraction.schema import EXTRACTION_SCHEMA, validate_schema
from src.extraction.fallback import needs_fallback

class ExtractionError(Exception):
    pass

def read_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def downscale_image_if_needed(image_bytes):
    # Determine if image needs downscaling (> ~5MB)
    # Since we are to do this deterministically to 3500px long edge, we can use PIL
    # But wait, we can just return image_bytes and scale=1.0 for now if it's small
    # To properly implement "deterministic downscale to 3500 px", let's use PIL
    import io
    from PIL import Image
    
    if len(image_bytes) <= 5 * 1024 * 1024:
        return image_bytes, 1.0
        
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    max_edge = max(w, h)
    
    if max_edge > 3500:
        scale = 3500.0 / max_edge
        new_w = int(w * scale)
        new_h = int(h * scale)
        # Affine deterministic downscale
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue(), scale
        
    return image_bytes, 1.0

def scale_back_boxes(data, scale):
    if scale == 1.0:
        return data
        
    inv_scale = 1.0 / scale
    fields = data.get("fields", {})
    for k, v in fields.items():
        box = v.get("box")
        if box:
            v["box"] = [int(b * inv_scale) for b in box]
    return data

def call_bedrock(image_bytes, model_id):
    # This is meant to call Bedrock Converse API with toolConfig
    # For now, it will be mocked in tests
    # When running live, we'd use boto3
    pass

def extract(canonical_image_bytes, config, model_client=None, cache_client=None):
    """
    extract(canonical_image, config) -> Extraction JSON or raise ExtractionError
    """
    import hashlib
    
    # Calculate ETag
    etag = hashlib.md5(canonical_image_bytes).hexdigest()
    
    if cache_client:
        cached = cache_client.get(etag)
        if cached:
            return cached
            
    downscaled_bytes, scale = downscale_image_if_needed(canonical_image_bytes)
    
    # model IDs from env or defaults
    haiku_id = os.environ.get("BEDROCK_HAIKU_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
    sonnet_id = os.environ.get("BEDROCK_SONNET_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
    
    prompt = read_prompt()
    
    def try_model(model_id):
        try:
            # We assume model_client is a callable for testing, otherwise we'd instantiate boto3
            if model_client:
                raw_json = model_client(downscaled_bytes, prompt, model_id, EXTRACTION_SCHEMA)
            else:
                raw_json = call_bedrock(downscaled_bytes, model_id)
                
            data = validate_schema(raw_json)
            return scale_back_boxes(data, scale)
        except Exception as e:
            return e
            
    res = try_model(haiku_id)
    
    # Trigger fallback if schema failed or needs_fallback
    if isinstance(res, Exception) or needs_fallback(res):
        res2 = try_model(sonnet_id)
        if isinstance(res2, Exception):
            raise ExtractionError("EXTRACTION_FAILED") from res2
        res = res2
        
    if cache_client:
        cache_client.put(etag, res)
        
    return res
