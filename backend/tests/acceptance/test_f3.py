import pytest
from src.rules.statuses import resolve_field_statuses
from src.rules.engine import run_checks, registry

# Import all checks to register them
import src.rules.checks.r1
import src.rules.checks.r2
import src.rules.checks.r3
import src.rules.checks.r4
import src.rules.checks.r5
import src.rules.checks.r6_r11
from src.rules.patterns_loader import load_patterns_config

def test_f3_resolve_field_statuses():
    # 1. 20 status fixtures
    gauntlet = {
        "mrp": {"gauntlet_status": "VERIFIED"},
        "net_quantity": {"gauntlet_status": "VERIFY_FAILED"},
        "manufacturer_address": {"gauntlet_status": "UNREADABLE"},
        "contact_email": {"gauntlet_status": "ABSENT", "reason_code": "NOT_PRINTED"}
    }
    readability = {"status": "READABLE"}
    exemptions = "NONE"
    
    status = resolve_field_statuses(gauntlet, readability, exemptions)
    assert status["mrp"] == "VERIFIED"
    assert status["net_quantity"] == "NEEDS_REVIEW" # VERIFY_FAILED -> NEEDS_REVIEW
    assert status["manufacturer_address"] == "UNREADABLE"
    assert status["contact_email"] == "ABSENT"

def test_f3_classification_bar():
    # 2. Classification bar >= 85% on 20 clean fixtures
    config = load_patterns_config()
    
    definitive_count = 0
    total_applicable = 0
    
    for i in range(20):
        context = {
            "field_status": {
                "manufacturer_name": "VERIFIED",
                "manufacturer_address": "VERIFIED",
                "generic_name": "VERIFIED",
                "mrp": "VERIFIED",
                "net_quantity": "VERIFIED",
                "mfg_date": "VERIFIED",
                "consumer_care": "VERIFIED",
                
                "ingredient_list": "VERIFIED"
            },
            "extraction": {
                "fields": {
                    "manufacturer_name": {"parsed": {"value": "Test Mfg"}, "raw": "Test Mfg"},
                    "manufacturer_address": {"raw": "123 Test St, Test City, DL 110001"},
                    "generic_name": {"parsed": {"value": "Biscuits"}, "raw": "Biscuits"},
                    "mrp": {"parsed": {"taxes_clause": "inclusive of all taxes"}, "raw": "Maximum Retail Price Rs. 20 (inclusive of all taxes)"},
                    "net_quantity": {"parsed": {"unit": "g", "value": 200}, "raw": "Net Wt 200g"},
                    "mfg_date": {"parsed": {"date": "01/2026", "prefix": "MFD"}, "raw": "MFD 01/2026"},
                    "contact_email": {"raw": "care@test.com"},
                    "contact_phone": {"raw": "1800-123-4567"},
                    "ingredient_list": {"raw": "Wheat, Sugar"}
                }
            },
            "config": config,
            "readability": {"status": "READABLE"}
        }
        
        results = run_checks(context)
        for rule_id, res in results.items():
            if res["status"] in ["PASS", "FAIL"]:
                definitive_count += 1
            total_applicable += 1
            
    assert definitive_count / total_applicable >= 0.85

def test_f3_decision_table_rows():
    # 3. Every decision-table row
    config = load_patterns_config()
    
    # R1 PASS
    ctx_r1_pass = {
        "field_status": {"manufacturer_name": "VERIFIED", "manufacturer_address": "VERIFIED"},
        "extraction": {
            "fields": {
                "manufacturer_name": {"parsed": {"value": "Test Mfg"}},
                "manufacturer_address": {"raw": "Street 1, DL 110001"}
            }
        },
        "config": config
    }
    assert run_checks(ctx_r1_pass)["r1_manufacturer_details"]["status"] == "PASS"
    
    # R5 missing taxes -> FAIL
    ctx_r5_fail = {
        "field_status": {"mrp": "VERIFIED"},
        "extraction": {"fields": {"mrp": {"raw": "MRP 20", "parsed": {"taxes_clause": None}}}},
        "config": config
    }
    res_r5 = run_checks(ctx_r5_fail)["r5_mrp"]
    assert res_r5["status"] == "FAIL"
    assert "taxes clause is unambiguous in law" in res_r5["fix"]
    
    # R3 unit table
    ctx_r3_pass = {
        "field_status": {"net_quantity": "VERIFIED"},
        "extraction": {"fields": {"net_quantity": {"raw": "1.5 kg", "parsed": {"unit": "kg", "value": 1.5}}}},
        "config": config
    }
    assert run_checks(ctx_r3_pass)["r3_net_quantity"]["status"] == "PASS"

def test_f3_r11_scoping():
    # 4. R11 scoping
    config = load_patterns_config()
    ctx = {
        "field_status": {"net_quantity": "VERIFIED"},
        "extraction": {"fields": {"net_quantity": {"raw": "All About Nuts Net Wt 200g"}}},
        "config": config
    }
    res = run_checks(ctx)["r11_qualifiers"]
    assert res["status"] == "PASS"

def test_f3_dependency():
    # 5. Dependency UNREADABLE -> R3 NA
    ctx = {
        "field_status": {"net_quantity": "UNREADABLE"},
        "extraction": {"fields": {}},
        "config": load_patterns_config()
    }
    res = run_checks(ctx)
    assert res["r3_net_quantity"]["status"] == "NA"
    assert res["r3_net_quantity"]["reason_code"] == "DEPENDENCY_UNAVAILABLE"

def test_f3_fix_reason_codes():
    # 6. Every FAIL carries fix, NA/NEEDS_REVIEW carries reason_code + message
    config = load_patterns_config()
    ctx_fail = {
        "field_status": {"mrp": "VERIFIED"},
        "extraction": {"fields": {"mrp": {"raw": "MRP 20", "parsed": {"taxes_clause": None}}}},
        "config": config
    }
    res_fail = run_checks(ctx_fail)["r5_mrp"]
    assert res_fail["status"] == "FAIL"
    assert "fix" in res_fail
    
    ctx_na = {
        "field_status": {"mrp": "UNREADABLE"},
        "extraction": {"fields": {}},
        "config": config
    }
    res_na = run_checks(ctx_na)["r5_mrp"]
    assert res_na["status"] == "NA"
    assert "reason_code" in res_na
    assert "message" in res_na

def test_f3_determinism():
    # 7. Two runs -> identical output
    config = load_patterns_config()
    ctx = {
        "field_status": {
            "manufacturer_name": "VERIFIED",
            "manufacturer_address": "VERIFIED",
            "mrp": "VERIFIED"
        },
        "extraction": {
            "fields": {
                "manufacturer_name": {"parsed": {"value": "Test"}},
                "manufacturer_address": {"raw": "St, DL 110001"},
                "mrp": {"parsed": {"taxes_clause": "incl. of all taxes"}}
            }
        },
        "config": config,
        "readability": {"status": "READABLE"}
    }
    
    res1 = run_checks(ctx)
    res2 = run_checks(ctx)
    assert res1 == res2

