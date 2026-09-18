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
    
    box = {"left": 0, "top": 0, "width": 100, "height": 20}
    
    assert check_g4({"raw": "MRP Rs. 20", "box": box}, word_index)
    assert not check_g4({"raw": "MRP Rs. 25", "box": box}, word_index)
    assert check_g4({"raw": "mrp rs 20", "box": box}, word_index) # normalize matches
    assert not check_g4({"raw": "Net Wt.", "box": box}, word_index)

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
    assert check_g6({"confidence": 0.95})
    assert check_g6({"confidence": 0.60})
    assert not check_g6({"confidence": 0.59})
    assert not check_g6({"confidence": None})
    assert not check_g6({})
