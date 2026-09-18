import pytest
from src.rules.statuses import resolve_field_statuses

def test_resolve_field_statuses_exempt():
    gauntlet = {
        "mrp": {"gauntlet_status": "VERIFIED", "reason_code": None}
    }
    res = resolve_field_statuses(gauntlet, True, exemptions="EXEMPT")
    assert res["mrp"] == "NA_EXEMPT"

def test_resolve_field_statuses_verified():
    gauntlet = {
        "mrp": {"gauntlet_status": "VERIFIED", "reason_code": None}
    }
    res = resolve_field_statuses(gauntlet, True, exemptions="NONE")
    assert res["mrp"] == "VERIFIED"

def test_resolve_field_statuses_absent():
    gauntlet = {
        "mrp": {"gauntlet_status": "NA", "reason_code": "NOT_PRINTED"}
    }
    res = resolve_field_statuses(gauntlet, True, exemptions="NONE")
    assert res["mrp"] == "ABSENT"

def test_resolve_field_statuses_unreadable():
    gauntlet = {
        "mrp": {"gauntlet_status": "NA", "reason_code": "UNREADABLE_IMAGE"}
    }
    res = resolve_field_statuses(gauntlet, False, exemptions="NONE")
    assert res["mrp"] == "UNREADABLE"

def test_resolve_field_statuses_needs_review():
    gauntlet = {
        "f1": {"gauntlet_status": "NEEDS_REVIEW", "reason_code": "LOW_CONFIDENCE"},
        "f2": {"gauntlet_status": "NEEDS_REVIEW", "reason_code": "EXTRACTION_MISS"},
        "f3": {"gauntlet_status": "NA", "reason_code": "VERIFY_FAILED"},
        "f4": {"gauntlet_status": "NA", "reason_code": "UNSUPPORTED_LANGUAGE"}
    }
    res = resolve_field_statuses(gauntlet, True, exemptions="NONE")
    assert res["f1"] == "NEEDS_REVIEW"
    assert res["f2"] == "NEEDS_REVIEW"
    assert res["f3"] == "NEEDS_REVIEW"
    assert res["f4"] == "NEEDS_REVIEW"
