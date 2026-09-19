import pytest
from src.rules.checks.r2 import check_r2

def test_check_r2_pass():
    context = {
        "field_status": {
            "generic_name": "VERIFIED"
        },
        "extraction": {
            "fields": {
                "generic_name": {
                    "raw": "generic"
                }
            }
        }
    }
    res = check_r2(context)
    assert res["status"] == "PASS"

def test_check_r2_fail():
    context = {
        "field_status": {
            "generic_name": "ABSENT"
        },
        "config": {
            "r2": {
                "fixes": {
                    "missing": "print the commodity's common/generic name"
                }
            }
        }
    }
    res = check_r2(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "print the commodity's common/generic name"

def test_r2_none():
    context = {"field_status": {"generic_name": "VERIFIED"}, "extraction": {"fields": {"generic_name": {"raw": None}}}}
    res = check_r2(context)
    assert res["status"] == "NA"
    assert res["reason_code"] == "DEPENDENCY_UNAVAILABLE"
