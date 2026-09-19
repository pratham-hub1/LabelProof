import os
import json
import base64
import time
import requests
from src.extraction.schema import EXTRACTION_SCHEMA, validate_schema
from src.extraction.fallback import needs_fallback

class ExtractionError(Exception):
    pass

def read_prompt():
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def extract_last_json_block(text):
    valid_blocks = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            stack = 0
            in_string = False
            escape = False
            for j in range(i, len(text)):
                c = text[j]
                if c == '\\' and not escape:
                    escape = True
                    continue
                if c == '"' and not escape:
                    in_string = not in_string
                if not in_string:
                    if c == '{': stack += 1
                    elif c == '}': stack -= 1
                escape = False
                if stack == 0:
                    block = text[i:j+1]
                    try:
                        parsed = json.loads(block)
                        if isinstance(parsed, dict):
                            valid_blocks.append((i, j, parsed))
                    except Exception:
                        pass
                    break
        i += 1
        
    if valid_blocks:
        valid_blocks.sort(key=lambda x: (x[1], -x[0]))
        return valid_blocks[-1][2]
    return None

def downscale_image_if_needed(image_bytes):
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

def call_openai_compatible(image_bytes, prompt, provider_config):
    base_url = provider_config["base_url"].rstrip("/")
    url = f"{base_url}/chat/completions"
    
    api_key_env = provider_config["api_key_env"]
    api_key = os.environ.get(api_key_env)
    if not api_key:
        raise ExtractionError(f"Missing API key in environment variable: {api_key_env}")
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    b64_img = base64.b64encode(image_bytes).decode("utf-8")
    
    payload = {
        "model": provider_config["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_img}"}}
                ]
            }
        ]
    }
    
    for k, v in provider_config.get("params", {}).items():
        payload[k] = v
        
    for attempt in range(2):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code in (429, 500, 502, 503, 504):
                if attempt == 0:
                    time.sleep(2)
                    continue
                else:
                    raise ExtractionError(f"HTTP {resp.status_code} after retry")
            
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            
            parsed_block = extract_last_json_block(content)
            if not parsed_block:
                raise ExtractionError("No valid JSON block found in response")
                
            return parsed_block
            
        except requests.exceptions.Timeout:
            raise ExtractionError("HTTP timeout")
        except requests.exceptions.RequestException as e:
            if attempt == 0 and getattr(e.response, 'status_code', None) in (429, 500, 502, 503, 504):
                time.sleep(2)
                continue
            raise ExtractionError(str(e))

def extract(canonical_image_bytes, config, model_client=None, cache_client=None):
    import hashlib
    
    providers_config = config.get("providers_config")
    if not providers_config:
        config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "llm_providers.config")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                providers_config = json.load(f)
        except Exception:
            providers_config = {
                "providers": [
                    {"id": "gemini", "base_url": "https://api", "model": "gemini", "api_key_env": "GEMINI_API_KEY"},
                    {"id": "nim", "base_url": "https://api", "model": "nim", "api_key_env": "NIM_API_KEY"}
                ],
                "active_provider": "gemini",
                "fallback_provider": "nim"
            }

    provider_map = {p["id"]: p for p in providers_config["providers"]}
    active_id = providers_config.get("active_provider")
    fallback_id = providers_config.get("fallback_provider")
    
    first_provider = provider_map[active_id]
    second_provider = provider_map[fallback_id]
    
    etag = hashlib.md5(canonical_image_bytes).hexdigest()
    
    if cache_client:
        cached = cache_client.get(etag)
        if cached:
            return cached
            
    downscaled_bytes, scale = downscale_image_if_needed(canonical_image_bytes)
    prompt = read_prompt()
    
    def try_provider(provider_conf):
        try:
            if model_client:
                raw_json = model_client(downscaled_bytes, prompt, provider_conf["id"], EXTRACTION_SCHEMA)
            else:
                raw_json = call_openai_compatible(downscaled_bytes, prompt, provider_conf)
                
            data = validate_schema(raw_json)
            return scale_back_boxes(data, scale)
        except Exception as e:
            return e
            
    res = try_provider(first_provider)
    
    if isinstance(res, Exception) or needs_fallback(res):
        res2 = try_provider(second_provider)
        if isinstance(res2, Exception):
            raise ExtractionError("EXTRACTION_FAILED") from res2
        res = res2
        
    if cache_client:
        cache_client.put(etag, res)
        
    return res
