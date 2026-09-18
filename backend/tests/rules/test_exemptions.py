import pytest
from src.rules.exemptions import evaluate_exemptions

def test_exemptions_not_applicable():
    ext = {"mrp": {"gauntlet_status": "VERIFIED", "parsed": {"value": 5.0}}}
    res = evaluate_exemptions(ext, {})
    assert res["status"] == "NONE"

def test_exemptions_nq_exempt():
    ext = {
        "net_quantity": {"gauntlet_status": "VERIFIED", "parsed": {"value": 8.0, "unit": "g"}},
        "generic_name": {"gauntlet_status": "VERIFIED", "raw": "Candies"}
    }
    res = evaluate_exemptions(ext, {})
    assert res["status"] == "EXEMPT"

def test_exemptions_none():
    ext = {
        "mrp": {"gauntlet_status": "VERIFIED", "parsed": {"value": 20.0}},
        "net_quantity": {"gauntlet_status": "VERIFIED", "parsed": {"value": 15.0, "unit": "g"}}
    }
    res = evaluate_exemptions(ext, {})
    assert res["status"] == "NONE"
