import sys
sys.path.insert(0, "backend")
from src.rules.engine import run_checks
import src.rules.checks.r1
import src.rules.checks.r2
import src.rules.checks.r3
import src.rules.checks.r4
import src.rules.checks.r5
import src.rules.checks.r6_r11
from src.rules.patterns_loader import load_patterns_config

config = load_patterns_config()
context = {
    "field_status": {
        "manufacturer_name": "VERIFIED",
        "manufacturer_address": "VERIFIED",
        "generic_name": "VERIFIED",
        "mrp": "VERIFIED",
        "net_quantity": "VERIFIED",
        "mfg_date": "VERIFIED",
        "contact_email": "VERIFIED",
        "contact_phone": "VERIFIED",
        "ingredient_list": "VERIFIED"
    },
    "extraction": {
        "fields": {
            "manufacturer_name": {"parsed": {"value": "Test Mfg"}, "raw": "Test Mfg"},
            "manufacturer_address": {"raw": "123 Test St, Test City, DL 110001"},
            "generic_name": {"parsed": {"value": "Biscuits"}, "raw": "Biscuits"},
            "mrp": {"parsed": {"taxes_clause": "inclusive of all taxes"}, "raw": "MRP Rs. 20 (inclusive of all taxes)"},
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
for k, v in results.items():
    if v["status"] not in ["PASS", "FAIL"]:
        print(f"{k}: {v['status']} ({v.get('reason_code')})")
