import pytest
from src.gauntlet.gates.g1 import check_g1
from src.gauntlet.gates.g2 import check_g2
from src.gauntlet.gates.g3 import check_g3
from src.gauntlet.gates.g4 import check_g4, normalize_text
from src.gauntlet.gates.g5 import check_g5
from src.gauntlet.gates.g6 import check_g6

def test_g1():
    image_meta = {"width": 1000, "height": 1000}
    assert check_g1({"box": {"left": 10, "top": 10, "width": 100, "height": 50}}, None, image_meta)
    assert not check_g1({"box": {"left": 1000, "top": 10, "width": 100, "height": 50}}, None, image_meta)
    assert not check_g1({"box": {"left": 10, "top": 10, "width": -10, "height": 50}}, None, image_meta)
    assert not check_g1({"box": None}, None, image_meta)
    
    # Asserting the CONTRACTS.md [left, top, right, bottom] array convention
    assert check_g1({"box": [10, 10, 110, 60]}, None, image_meta) # right=110, bottom=60 -> width=100, height=50
    assert not check_g1({"box": [110, 10, 10, 60]}, None, image_meta) # right=10, left=110 -> width=-100

def test_g2():
    assert check_g2({"raw": "hello"})
    assert not check_g2({"raw": ""})
    assert not check_g2({"raw": None})
    assert not check_g2({})

def test_g3():
    # Null parsed -> passes
    assert check_g3({"raw": "MRP 20", "parsed": None})
    
    # Matching digits
    assert check_g3({"raw": "MRP 20", "parsed": {"value": 20}})
    assert not check_g3({"raw": "MRP 25", "parsed": {"value": 20}})
    
    # Unit matches
    assert check_g3({"raw": "Net Wt. 200g", "parsed": {"value": 200, "unit": "g"}})
    assert not check_g3({"raw": "Net Wt. 200", "parsed": {"value": 200, "unit": "g"}})
    
    # Phone digits
    assert check_g3({"raw": "Call 1800-123", "parsed": {"phone": "1800123"}})
    assert not check_g3({"raw": "Call 1800-123", "parsed": {"phone": "1800999"}})

def test_g4():
    word_index = [
        {"word": "MRP", "box": {"left": 10, "top": 10, "width": 30, "height": 10}},
        {"word": "Rs.", "box": {"left": 50, "top": 10, "width": 20, "height": 10}},
        {"word": "20", "box": {"left": 80, "top": 10, "width": 20, "height": 10}}
    ]
    
    # Box is now optional/ignored initially
    claim1 = {"raw": "MRP Rs. 20"}
    assert check_g4(claim1, word_index)
    # The box should be derived as the union of the matched words:
    # Left min: 10, Top min: 10
    # Right max: 80+20 = 100, Bottom max: 10+10 = 20
    assert claim1["box"] == [10, 10, 100, 20]
    
    claim2 = {"raw": "MRP Rs. 25"}
    assert not check_g4(claim2, word_index)
    
    claim3 = {"raw": "mrp rs 20"}
    assert check_g4(claim3, word_index)
    
    claim4 = {"raw": "Net Wt."}
    assert not check_g4(claim4, word_index)

def test_g5():
    word_index = [
        {"word": "MRP", "box": {"left": 10, "top": 10, "width": 30, "height": 10}},
        {"word": "20", "box": {"left": 50, "top": 10, "width": 20, "height": 10}}
    ]
    
    anchors = {
        "mrp": [r"\bmrp\b", r"\bmax\.?\s*retail\s*price\b"]
    }
    
    box = {"left": 0, "top": 0, "width": 100, "height": 20}
    
    # Anchored field, anchor present
    assert check_g5({"box": box}, "mrp", word_index, anchors)
    
    # Anchored field, anchor missing
    box_empty = {"left": 100, "top": 100, "width": 10, "height": 10}
    assert not check_g5({"box": box_empty}, "mrp", word_index, anchors)
    
    # Unanchored field
    assert check_g5({"box": box}, "generic_name", word_index, anchors)

def test_g6():
    valid_claim = {"raw": "abc", "parsed": {}, "box": {}, "confidence": 0.95}
    assert check_g6(valid_claim)
    
    invalid_claim_conf = {"raw": "abc", "parsed": {}, "box": {}, "confidence": 0.50}
    assert not check_g6(invalid_claim_conf)
    
    missing_key_claim = {"raw": "abc", "confidence": 0.95}
    assert not check_g6(missing_key_claim)
