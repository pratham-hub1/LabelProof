import json
from src.rules.exemptions import evaluate_exemptions
from src.rules.statuses import resolve_field_statuses

def load_tobacco_config():
    with open("config/tobacco.config", "r") as f:
        return json.load(f)

def test_f4_sachet_exempt():
    # 1. Sachet <=10 g (clean generic name) -> EXEMPT
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "g", "value": 10}
        },
        "generic_name": {
            "gauntlet_status": "VERIFIED",
            "raw": "Biscuits"
        }
    }
    config = load_tobacco_config()
    res = evaluate_exemptions(fields, config)
    assert res["status"] == "EXEMPT"
    
    # All checks NA, handled by engine (we can check field_status_map)
    gauntlet = {
        "mrp": {"gauntlet_status": "VERIFIED"},
        "net_quantity": {"gauntlet_status": "VERIFIED"}
    }
    field_status = resolve_field_statuses(gauntlet, {"status": "READABLE"}, res)
    assert field_status["mrp"] == "NA_EXEMPT"

def test_f4_sachet_gutkha():
    # 2. Sachet <=10g + gutkha -> NEEDS_REVIEW
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "g", "value": 5}
        },
        "generic_name": {
            "gauntlet_status": "VERIFIED",
            "raw": "Premium Gutkha"
        }
    }
    res = evaluate_exemptions(fields, load_tobacco_config())
    assert res["status"] == "NEEDS_REVIEW"
    assert "tobacco" in res["reason"]

def test_f4_unverified_commodity():
    # 3. Sachet <=10g + generic_name ABSENT -> NEEDS_REVIEW
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "g", "value": 5}
        },
        "generic_name": {
            "gauntlet_status": "ABSENT"
        }
    }
    res = evaluate_exemptions(fields, load_tobacco_config())
    assert res["status"] == "NEEDS_REVIEW"
    assert "unverified" in res["reason"]

def test_f4_30kg():
    # 4. 30 kg package -> NEEDS_REVIEW Rule 3
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "kg", "value": 30}
        }
    }
    res = evaluate_exemptions(fields, load_tobacco_config())
    assert res["status"] == "NEEDS_REVIEW"
    assert "Chapter II" in res["reason"]

def test_f4_pcs():
    # 5. "6 pcs" -> no exemption
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "pcs", "value": 6}
        }
    }
    res = evaluate_exemptions(fields, load_tobacco_config())
    assert res["status"] == "NONE"

def test_f4_10_5g():
    # 6. 10.5g boundary -> no exemption
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "g", "value": 10.5}
        }
    }
    res = evaluate_exemptions(fields, load_tobacco_config())
    assert res["status"] == "NONE"

def test_f4_determinism():
    # 8. Determinism
    fields = {
        "net_quantity": {
            "gauntlet_status": "VERIFIED",
            "parsed": {"unit": "g", "value": 10}
        },
        "generic_name": {
            "gauntlet_status": "VERIFIED",
            "raw": "Snack"
        }
    }
    config = load_tobacco_config()
    res1 = evaluate_exemptions(fields, config)
    res2 = evaluate_exemptions(fields, config)
    assert res1 == res2
