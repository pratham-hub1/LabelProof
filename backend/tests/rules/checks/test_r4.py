import pytest
from src.rules.checks.r4 import check_r4

def test_check_r4_pass():
    context = {
        "extraction": {
            "fields": {
                "mfg_date": {
                    "raw": "MFG 08/2026"
                }
            }
        },
        "config": {
            "r4": {
                "date_formats": ["%m/%Y"],
                "prefixes": ["MFG"]
            }
        }
    }
    res = check_r4(context)
    assert res["status"] == "PASS"

def test_check_r4_fail():
    context = {
        "extraction": {
            "fields": {
                "mfg_date": {
                    "raw": "Made in 2026"
                }
            }
        },
        "config": {
            "r4": {
                "date_formats": ["%m/%Y"],
                "prefixes": ["MFG"],
                "fixes": {"invalid": "valid formats"}
            }
        }
    }
    res = check_r4(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "valid formats"
