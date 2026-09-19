import pytest
from src.rules.checks.r5 import check_r5

def test_check_r5_pass():
    context = {
        "extraction": {
            "fields": {
                "mrp": {
                    "raw": "Maximum Retail Price Rs. 20 (inclusive of all taxes)"
                }
            }
        },
        "config": {
            "r5": {
                "taxes_clauses": ["(inclusive of all taxes)"]
            }
        }
    }
    res = check_r5(context)
    assert res["status"] == "PASS"

def test_check_r5_needs_review_shorthand():
    context = {
        "extraction": {
            "fields": {
                "mrp": {
                    "raw": "MRP Rs. 20 (inclusive of all taxes)"
                }
            }
        },
        "config": {
            "r5": {
                "taxes_clauses": ["(inclusive of all taxes)"]
            }
        }
    }
    res = check_r5(context)
    assert res["status"] == "NEEDS_REVIEW"

def test_check_r5_fail_taxes():
    context = {
        "extraction": {
            "fields": {
                "mrp": {
                    "raw": "Maximum Retail Price Rs. 20"
                }
            }
        },
        "config": {
            "r5": {
                "taxes_clauses": ["(inclusive of all taxes)"],
                "fixes": {"missing_taxes": "taxes clause is unambiguous in law"}
            }
        }
    }
    res = check_r5(context)
    assert res["status"] == "FAIL"
    assert res["fix"] == "taxes clause is unambiguous in law"

def test_check_r5_needs_review_multiple():
    context = {
        "extraction": {
            "fields": {
                "mrp": {
                    "raw": "Maximum Retail Price Rs. 20 (inclusive of all taxes) Rs. 25 in some states"
                }
            }
        },
        "config": {
            "r5": {
                "taxes_clauses": ["(inclusive of all taxes)"],
                "fixes": {"missing_taxes": "taxes clause is unambiguous in law"}
            }
        }
    }
    res = check_r5(context)
    assert res["status"] == "NEEDS_REVIEW"

def test_r5_none():
    context = {"extraction": {"fields": {"mrp": {"raw": None}}}}
    res = check_r5(context)
    assert res["status"] == "NA"
    assert res["reason_code"] == "DEPENDENCY_UNAVAILABLE"
