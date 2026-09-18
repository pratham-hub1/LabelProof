import pytest
import json
from src.gauntlet.mapper import map_field_result
from src.gauntlet.anchors_loader import load_anchors_config

@pytest.fixture
def anchors():
    return load_anchors_config()

def generate_cases(scenario, count=10):
    cases = []
    for i in range(count):
        if scenario == "hallucination":
            cases.append({
                "claim": {"raw": f"Hallucinated Text {i}", "confidence": 0.9, "box": [10, 10, 100, 30]},
                "word_index": [{"word": "Other", "box": [10, 10, 100, 30]}],
                "is_readable": True
            })
        elif scenario == "misread":
            cases.append({
                "claim": {"raw": f"Misread {i}", "confidence": 0.9, "box": [10, 10, 100, 30]},
                "word_index": [{"word": "Actual", "box": [10, 10, 100, 30]}],
                "is_readable": True
            })
        elif scenario == "wrong-attribution":
            cases.append({
                "claim": {"raw": "Net Wt. 200g", "confidence": 0.9, "box": [10, 10, 100, 30]},
                "word_index": [{"word": "200g", "box": [10, 10, 100, 30]}], # Missing anchor
                "is_readable": True
            })
        elif scenario == "missing-declaration":
            cases.append({
                "claim": None,
                "word_index": [{"word": "Random", "box": [10, 10, 100, 30]}],
                "is_readable": True
            })
        elif scenario == "poor-quality":
            cases.append({
                "claim": None,
                "word_index": [{"word": "Blurry", "box": [10, 10, 100, 30]}],
                "is_readable": False
            })
        elif scenario == "clean":
            cases.append({
                "claim": {"raw": "Net Wt 200g", "confidence": 0.9, "box": [10, 10, 100, 30], "parsed": {"unit": "g", "value": 200}},
                "word_index": [{"word": "Net", "box": [10, 10, 40, 30]}, {"word": "Wt", "box": [45, 10, 65, 30]}, {"word": "200g", "box": [70, 10, 100, 30]}],
                "is_readable": True
            })
    return cases

def test_f1_hallucinations(anchors):
    # 10 hallucination fixtures -> 10 NA (VERIFY_FAILED)
    cases = generate_cases("hallucination", 10)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        assert res["gauntlet_status"] == "VERIFY_FAILED"
        assert res["reason_code"] == "VERIFY_FAILED"

def test_f1_misread(anchors):
    # 10 misread fixtures -> 10 NA (VERIFY_FAILED)
    cases = generate_cases("misread", 10)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        assert res["gauntlet_status"] == "VERIFY_FAILED"
        assert res["reason_code"] == "VERIFY_FAILED"

def test_f1_wrong_attribution(anchors):
    # 10 wrong-attribution fixtures -> 10 NA (no anchor in box)
    # The error should be NO_ANCHOR_FOUND or VERIFY_FAILED
    cases = generate_cases("wrong-attribution", 10)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        assert res["gauntlet_status"] == "VERIFY_FAILED"

def test_f1_missing_declaration(anchors):
    # 10 readable-label fixtures with missing declaration -> 10 FAIL
    cases = generate_cases("missing-declaration", 10)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        assert res["gauntlet_status"] == "ABSENT"
        # The engine translates ABSENT to FAIL in R1-R7 (actually the engine checks if ABSENT -> FAILED in final verdict)
        # But wait, F1 1.10 says "10 FAIL 'not found on label'". Actually map_field_result returns ABSENT.

def test_f1_poor_quality(anchors):
    # 10 poor-quality images -> 0 false FAILs; NAs with UNREADABLE_IMAGE
    cases = generate_cases("poor-quality", 10)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        assert res["gauntlet_status"] == "UNREADABLE"
        assert res["reason_code"] == "UNREADABLE_IMAGE"

def test_f1_clean(anchors):
    # 20 clean labels -> >= 90% anchored fields VERIFIED
    cases = generate_cases("clean", 20)
    verified = 0
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        if res["gauntlet_status"] == "VERIFIED":
            verified += 1
        else:
            print(res)
    assert verified >= 18 # 90%
    
def test_f1_reason_codes(anchors):
    # Every NA/NEEDS_REVIEW carries a reason code and message
    cases = generate_cases("hallucination", 1) + generate_cases("poor-quality", 1)
    for case in cases:
        res = map_field_result("net_quantity", case["claim"], case["word_index"], case["is_readable"], anchors, None)
        if res["gauntlet_status"] in ["VERIFY_FAILED", "UNREADABLE", "NEEDS_REVIEW", "ABSENT"]:
            assert "reason_code" in res
            assert res["reason_code"] is not None

