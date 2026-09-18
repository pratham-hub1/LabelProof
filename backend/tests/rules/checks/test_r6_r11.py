import pytest
from src.rules.checks.r6_r11 import check_r6, check_r11

def test_check_r6_pass():
    context = {
        "field_status": {
            "consumer_care": "VERIFIED"
        }
    }
    res = check_r6(context)
    assert res["status"] == "PASS"

def test_check_r6_fail():
    context = {
        "field_status": {
            "consumer_care": "ABSENT"
        }
    }
    res = check_r6(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "no contactable channel"

def test_check_r11_pass_third_schedule():
    context = {
        "extraction": {
            "fields": {
                "generic_name": {"raw": "Biscuits"},
                "net_quantity": {"raw": "minimum 200g"}
            }
        },
        "config": {
            "r11": {
                "third_schedule": ["Biscuits"],
                "qualifiers": ["minimum"]
            }
        }
    }
    res = check_r11(context)
    assert res["status"] == "PASS"

def test_check_r11_fail_qualifier():
    context = {
        "extraction": {
            "fields": {
                "generic_name": {"raw": "Snack"},
                "net_quantity": {"raw": "minimum 200g"}
            }
        },
        "config": {
            "r11": {
                "third_schedule": ["Biscuits"],
                "qualifiers": ["minimum"],
                "fixes": {"misleading": "misleading qualifier present"}
            }
        }
    }
    res = check_r11(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "misleading qualifier present"

def test_check_r11_pass_clean():
    context = {
        "extraction": {
            "fields": {
                "generic_name": {"raw": "Snack"},
                "net_quantity": {"raw": "200g"}
            }
        },
        "config": {
            "r11": {
                "third_schedule": ["Biscuits"],
                "qualifiers": ["minimum"]
            }
        }
    }
    res = check_r11(context)
    assert res["status"] == "PASS"
