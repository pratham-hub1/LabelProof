import pytest
from src.gauntlet.mapper import map_field_result, load_reasons_config

def test_load_reasons():
    config = load_reasons_config()
    assert "NOT_PRINTED" in config
    assert "message" in config["NOT_PRINTED"]

def test_map_field_result_missing_vs_unreadable():
    anchors = {"mrp": [r"\bmrp\b"]}
    word_index = [{"word": "MRP", "box": {"left": 0, "top": 0, "width": 10, "height": 10}}]
    
    # R true, no claim, anchor present -> EXTRACTION_MISS
    res = map_field_result("mrp", None, word_index, is_readable=True, anchors_config=anchors)
    assert res["gauntlet_status"] == "NEEDS_REVIEW"
    assert res["reason_code"] == "EXTRACTION_MISS"
    
    # R true, no claim, no anchor -> NOT_PRINTED
    res = map_field_result("mrp", None, [], is_readable=True, anchors_config=anchors)
    assert res["gauntlet_status"] == "ABSENT"
    assert res["reason_code"] == "NOT_PRINTED"
    
    # R false, no claim -> UNREADABLE
    res = map_field_result("mrp", None, [], is_readable=False, anchors_config=anchors)
    assert res["gauntlet_status"] == "UNREADABLE"
    assert res["reason_code"] == "UNREADABLE_IMAGE"

def test_map_field_result_devanagari():
    # Devanagari only failure
    claim = {"raw": "आलू", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}
    # Fails G4 since word_index is empty
    res = map_field_result("generic_name", claim, [], is_readable=True, anchors_config={})
    assert res["gauntlet_status"] == "NEEDS_REVIEW"
    assert res["reason_code"] == "UNSUPPORTED_LANGUAGE"

def test_map_field_result_verify_failed(mocker):
    # Mock gates to fail
    mocker.patch("src.gauntlet.mapper.check_g1", return_value=False)
    claim = {"raw": "hello", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}
    res = map_field_result("generic_name", claim, [], is_readable=True, anchors_config={})
    assert res["gauntlet_status"] == "VERIFY_FAILED"
    assert res["reason_code"] == "VERIFY_FAILED"

def test_map_field_result_low_confidence(mocker):
    # Mock G1-G5 pass, G6 fail
    mocker.patch("src.gauntlet.mapper.check_g1", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g2", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g3", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g4", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g5", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g6", return_value=False)
    
    claim = {"raw": "hello", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.5}
    res = map_field_result("generic_name", claim, [], is_readable=True, anchors_config={})
    assert res["gauntlet_status"] == "NEEDS_REVIEW"
    assert res["reason_code"] == "LOW_CONFIDENCE"

def test_map_field_result_verified(mocker):
    mocker.patch("src.gauntlet.mapper.check_g1", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g2", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g3", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g4", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g5", return_value=True)
    mocker.patch("src.gauntlet.mapper.check_g6", return_value=True)
    
    claim = {"raw": "hello", "box": {"left": 0, "top": 0, "width": 10, "height": 10}, "confidence": 0.9}
    res = map_field_result("generic_name", claim, [], is_readable=True, anchors_config={})
    assert res["gauntlet_status"] == "VERIFIED"
    assert res["reason_code"] is None
