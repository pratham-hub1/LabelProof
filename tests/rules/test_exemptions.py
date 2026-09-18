import pytest
from src.rules.exemptions import evaluate_exemptions

def test_exemptions_mrp():
    ext = {"fields": {"mrp": {"parsed": {"value": 5.0}}}}
    assert evaluate_exemptions(ext) == "EXEMPT"

def test_exemptions_nq():
    ext = {"fields": {"net_quantity": {"parsed": {"value": 8.0, "unit": "g"}}}}
    assert evaluate_exemptions(ext) == "EXEMPT"

def test_exemptions_none():
    ext = {
        "fields": {
            "mrp": {"parsed": {"value": 20.0}},
            "net_quantity": {"parsed": {"value": 15.0, "unit": "g"}}
        }
    }
    assert evaluate_exemptions(ext) == "NONE"
