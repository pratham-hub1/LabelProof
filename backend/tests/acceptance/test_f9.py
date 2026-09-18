import pytest
import io
import json
from PIL import Image
from src.extraction.client import extract, ExtractionError
from src.extraction.schema import EXTRACTION_SCHEMA

def create_image(size=(100, 100), color=(255, 255, 255)):
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()

def create_valid_json(confidence=0.9):
    return {
        "schema_version": "1.0",
        "source_type": "photo",
        "image": {"width": 100, "height": 100},
        "language": "en",
        "brand_guess": "Test Brand",
        "fields": {
            "manufacturer_name": {"raw": "A", "parsed": {"value": "A"}, "confidence": confidence, "box": [0,0,10,10]},
            "manufacturer_address": {"raw": "B", "parsed": {"value": "B"}, "confidence": confidence, "box": [0,0,10,10]},
            "generic_name": {"raw": "C", "parsed": {"value": "C"}, "confidence": confidence, "box": [0,0,10,10]},
            "net_quantity": {"raw": "D", "parsed": {"value": 1, "unit": "g"}, "confidence": confidence, "box": [0,0,10,10]},
            "mfg_date": {"raw": "E", "parsed": {"date": "01/2026"}, "confidence": confidence, "box": [0,0,10,10]},
            "mrp": {"raw": "F", "parsed": {"value": 10}, "confidence": confidence, "box": [0,0,10,10]},
            "consumer_care": {"raw": "G", "parsed": {"phone": "123"}, "confidence": confidence, "box": [0,0,10,10]}
        }
    }

class MockCache:
    def __init__(self):
        self.store = {}
    def get(self, key):
        return self.store.get(key)
    def put(self, key, val):
        self.store[key] = val

class MockModelClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []
        
    def __call__(self, img_bytes, prompt, model_id, schema):
        self.calls.append(model_id)
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp

def test_f9_schema_valid():
    # 1. Schema-valid fixture -> one Haiku call
    img = create_image()
    valid_json = create_valid_json()
    model = MockModelClient([valid_json])
    
    res = extract(img, {}, model_client=model)
    
    assert len(model.calls) == 1
    assert "haiku" in model.calls[0]
    assert res == valid_json

def test_f9_malformed_retry():
    # 2. Malformed -> Sonnet retry
    img = create_image()
    valid_json = create_valid_json()
    model = MockModelClient([{"bad": "json"}, valid_json])
    
    res = extract(img, {}, model_client=model)
    
    assert len(model.calls) == 2
    assert "haiku" in model.calls[0]
    assert "sonnet" in model.calls[1]
    assert res == valid_json

def test_f9_both_fail():
    # 3. Both fail -> ExtractionError
    img = create_image()
    model = MockModelClient([{"bad": "json"}, {"bad": "json"}])
    
    with pytest.raises(ExtractionError) as excinfo:
        extract(img, {}, model_client=model)
    assert "EXTRACTION_FAILED" in str(excinfo.value)

def test_f9_weak_read_retry():
    # 4. 2 fields < 0.60 -> retry
    img = create_image()
    weak_json = create_valid_json()
    weak_json["fields"]["manufacturer_name"]["confidence"] = 0.5
    weak_json["fields"]["manufacturer_address"]["confidence"] = 0.5
    
    valid_json = create_valid_json()
    model = MockModelClient([weak_json, valid_json])
    
    res = extract(img, {}, model_client=model)
    
    assert len(model.calls) == 2
    assert "haiku" in model.calls[0]
    assert "sonnet" in model.calls[1]
    assert res == valid_json

def test_f9_one_weak_field_no_retry():
    # 4. 1 weak field -> no retry
    img = create_image()
    weak_json = create_valid_json()
    weak_json["fields"]["manufacturer_name"]["confidence"] = 0.5
    
    model = MockModelClient([weak_json])
    
    res = extract(img, {}, model_client=model)
    
    assert len(model.calls) == 1
    assert res == weak_json

def test_f9_cache_hit():
    # 5. Cache hit -> zero calls
    img = create_image()
    valid_json = create_valid_json()
    cache = MockCache()
    
    model = MockModelClient([valid_json])
    res1 = extract(img, {}, model_client=model, cache_client=cache)
    assert len(model.calls) == 1
    
    model2 = MockModelClient([])
    res2 = extract(img, {}, model_client=model2, cache_client=cache)
    assert len(model2.calls) == 0
    assert res1 == res2

def test_f9_oversize_image(monkeypatch):
    # 6. Oversize image (>5MB) -> deterministic downscale, boxes scaled exactly
    # We will mock downscale_image_if_needed
    import src.extraction.client
    original_downscale = src.extraction.client.downscale_image_if_needed
    
    def mock_downscale(image_bytes):
        # Force a scale factor of 0.5
        return image_bytes, 0.5
        
    monkeypatch.setattr(src.extraction.client, "downscale_image_if_needed", mock_downscale)
    
    img = create_image()
    # Mock model returns a box at [0, 0, 50, 50] on the downscaled image
    valid_json = create_valid_json()
    valid_json["fields"]["manufacturer_name"]["box"] = [0, 0, 50, 50]
    model = MockModelClient([valid_json])
    
    res = extract(img, {}, model_client=model)
    
    # The box should be scaled back up by 1/0.5 = 2.0 -> [0, 0, 100, 100]
    assert res["fields"]["manufacturer_name"]["box"] == [0, 0, 100, 100]

def test_f9_determinism():
    # 7. Two runs -> schema-valid both times
    img = create_image()
    valid_json = create_valid_json()
    model = MockModelClient([valid_json, valid_json])
    
    res1 = extract(img, {}, model_client=model)
    res2 = extract(img, {}, model_client=model)
    assert res1 == res2
