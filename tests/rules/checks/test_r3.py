import pytest
from src.rules.checks.r3 import check_r3

def test_check_r3_pass():
    context = {
        "extraction": {
            "fields": {
                "net_quantity": {
                    "parsed": {"value": 10, "unit": "g"}
                }
            }
        }
    }
    assert check_r3(context)["status"] == "PASS"

def test_check_r3_fail_invalid_unit():
    context = {
        "extraction": {
            "fields": {
                "net_quantity": {
                    "parsed": {"value": 10, "unit": "oz"}
                }
            }
        }
    }
    res = check_r3(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "print standard unit (e.g. g, ml, pcs)"

def test_check_r3_fail_missing_parsed():
    context = {
        "extraction": {
            "fields": {
                "net_quantity": {
                    "raw": "10 oz"
                }
            }
        }
    }
    res = check_r3(context)
    assert res["status"] == "FAIL"

def test_check_r3_fail_sub_kg():
    context = {
        'extraction': {
            'fields': {
                'net_quantity': {
                    'parsed': {'value': 0.5, 'unit': 'kg'}
                }
            }
        }
    }
    res = check_r3(context)
    assert res['status'] == 'FAIL'
    assert res['fix'] == '<1 kg must be grams / <1 L must be ml'
