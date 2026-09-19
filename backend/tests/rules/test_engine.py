import pytest
from src.rules.engine import run_checks, registry

# Register a mock check
@registry.register("mock_r1", requires=["generic_name"])
def mock_r1_check(context):
    return {"status": "PASS"}

@registry.register("mock_r2", requires=["net_quantity"])
def mock_r2_check(context):
    return {"status": "FAIL", "fix": "Add unit"}

@registry.register("mock_r3", requires=[])
def mock_r3_check(context):
    return {"status": "PASS"}

def test_run_checks_all_verified():
    context = {
        "field_status": {
            "generic_name": "VERIFIED",
            "net_quantity": "VERIFIED"
        },
        "extraction": {"fields": {"net_quantity": {"parsed": {"value": 10, "unit": "g"}}, "mfg_date": {"raw": "10/2025"}}},
        "config": {},
        "word_index": []
    }
    res = run_checks(context)
    
    assert res["mock_r1"]["status"] == "PASS"
    assert res["mock_r2"]["status"] == "FAIL"
    assert res["mock_r3"]["status"] == "PASS"

def test_run_checks_dependency_missing():
    context = {
        "field_status": {
            "generic_name": "VERIFIED",
            "net_quantity": "UNREADABLE"
        },
        "extraction": {"fields": {"net_quantity": {"parsed": {"value": 10, "unit": "g"}}, "mfg_date": {"raw": "10/2025"}}},
        "config": {},
        "word_index": []
    }
    res = run_checks(context)
    
    assert res["mock_r1"]["status"] == "PASS"
    assert res["mock_r2"]["status"] == "NA"
    assert res["mock_r2"]["reason_code"] == "DEPENDENCY_UNAVAILABLE"
    assert res["mock_r3"]["status"] == "PASS"

def test_run_checks_dependency_absent():
    context = {
        "field_status": {
            "generic_name": "ABSENT",
            "net_quantity": "VERIFIED"
        },
        "extraction": {"fields": {"net_quantity": {"parsed": {"value": 10, "unit": "g"}}, "mfg_date": {"raw": "10/2025"}}},
        "config": {},
        "word_index": []
    }
    res = run_checks(context)
    
    # ABSENT is allowed for dependency check (the rule handles ABSENT logic)
    assert res["mock_r1"]["status"] == "PASS"
