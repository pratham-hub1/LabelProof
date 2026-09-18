import pytest
from src.geometry.check_r8 import check_r8, detect_embossed, rgb_to_lab, calc_contrast

def test_check_r8_pass():
    config = {
        "rule7_table": [
            {"max_area": 50, "normal": 1.0, "molded": 1.5},
            {"max_area": 100, "normal": 1.5, "molded": 3.0},
            {"max_area": 99999, "normal": 2.5, "molded": 4.0}
        ]
    }
    
    # Area 75 cm^2, not molded -> required_mm = 1.5
    # measured = 2.0, sigma_scale = 0.05 -> sigma_H = 0.1
    # 2.0 - 0.3 = 1.7 >= 1.5 -> PASS
    res = check_r8(2.0, 75, False, 0.05, config)
    assert res["status"] == "PASS"

def test_check_r8_fail():
    config = {
        "rule7_table": [
            {"max_area": 100, "normal": 1.5, "molded": 3.0},
            {"max_area": 99999, "normal": 2.5, "molded": 4.0}
        ]
    }
    # Area 75 cm^2, required 1.5
    # measured = 1.0, sigma_H = 0.05
    # 1.0 + 0.15 = 1.15 < 1.5 -> FAIL
    res = check_r8(1.0, 75, False, 0.05, config)
    assert res["status"] == "FAIL"

def test_check_r8_needs_review():
    config = {
        "rule7_table": [
            {"max_area": 100, "normal": 1.5, "molded": 3.0},
            {"max_area": 99999, "normal": 2.5, "molded": 4.0}
        ]
    }
    # Boundary: measured = 1.5, sigma_H = 0.075
    # 1.5 + 3*sigma = 1.725 (not < 1.5)
    # 1.5 - 3*sigma = 1.275 (not >= 1.5)
    # -> NEEDS_REVIEW
    res = check_r8(1.5, 75, False, 0.05, config)
    assert res["status"] == "NEEDS_REVIEW"

def test_detect_embossed():
    config = {
        "embossed": {
            "delta_e_max": 10,
            "pale_print_delta_e_min": 15,
            "contrast_max": 2.5
        }
    }
    
    # Same color (MOLDED)
    assert detect_embossed((100, 100, 100), (102, 102, 102), config) == "MOLDED"
    
    # Very different color, low contrast (PALE_PRINT)
    # Red and Green might have high delta_E but similar luminance
    assert detect_embossed((0, 255, 255), (0, 255, 0), config) == "PALE_PRINT"
    
    # Needs review (between 10 and 15)
    # We can skip exact color math testing if we just trust the function, but let's test one
    # If delta_E is 12 -> NEEDS_REVIEW
    # Or if contrast > 2.5 -> NEEDS_REVIEW (if delta_E < 10)
    assert detect_embossed((0, 0, 0), (255, 255, 255), config) == "NEEDS_REVIEW" # high contrast
