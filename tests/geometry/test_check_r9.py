import pytest
import numpy as np
from src.geometry.check_r9 import check_r9

def test_check_r9_pass():
    quantity_box = {"left": 100, "top": 100, "width": 50, "height": 20}
    h_px = 10
    
    # Word index is empty
    res = check_r9([], quantity_box, h_px, None)
    assert res["status"] == "PASS"

def test_check_r9_fail_word():
    quantity_box = {"left": 100, "top": 100, "width": 50, "height": 20}
    h_px = 10
    
    # A word at x=85, y=100. It intersects the left exclusion zone (100 - 2*10 = 80).
    word_index = [
        {"word": "Test", "box": {"left": 85, "top": 100, "width": 10, "height": 10}}
    ]
    
    res = check_r9(word_index, quantity_box, h_px, None)
    assert res["status"] == "FAIL"

def test_check_r9_fail_ink():
    quantity_box = {"left": 100, "top": 100, "width": 50, "height": 20}
    h_px = 10
    
    ink_map = np.zeros((300, 300), dtype=bool)
    
    # Add heavy ink in the zone (top zone: y=90 to 100)
    ink_map[90:100, 100:150] = True
    
    res = check_r9([], quantity_box, h_px, ink_map)
    assert res["status"] == "FAIL"
