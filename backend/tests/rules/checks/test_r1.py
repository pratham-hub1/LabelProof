import pytest
from src.rules.checks.r1 import check_r1

def test_check_r1_missing():
    context = {
        "field_status": {
            "manufacturer_name": "VERIFIED",
            "manufacturer_address": "ABSENT"
        }
    }
    res = check_r1(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "print the manufacturer's name and address"

def test_check_r1_pass():
    context = {
        "field_status": {
            "manufacturer_name": "VERIFIED",
            "manufacturer_address": "VERIFIED"
        },
        "extraction": {
            "fields": {
                "manufacturer_address": {
                    "raw": "123 Street, Mumbai 400001, Maharashtra"
                }
            }
        },
        "config": {
            "r1": {
                "pin_regex": "\\b\\d{6}\\b",
                "states": ["Maharashtra"]
            }
        }
    }
    res = check_r1(context)
    assert res["status"] == "PASS"

def test_check_r1_missing_state():
    context = {
        "field_status": {
            "manufacturer_name": "VERIFIED",
            "manufacturer_address": "VERIFIED"
        },
        "extraction": {
            "fields": {
                "manufacturer_address": {
                    "raw": "123 Street, Mumbai 400001"
                }
            }
        },
        "config": {
            "r1": {
                "pin_regex": "\\b\\d{6}\\b",
                "states": ["Maharashtra"]
            }
        }
    }
    res = check_r1(context)
    assert res["status"] == "NEEDS_REVIEW"

def test_r1_none():
    context = {"extraction": {"fields": {"manufacturer_name": {"raw": None}, "manufacturer_address": {"raw": None}}}}
    res = check_r1(context)
    assert res["status"] == "NA"
    assert res["reason_code"] == "DEPENDENCY_UNAVAILABLE"
