import re
from datetime import datetime
from src.rules.engine import registry

@registry.register("r4_mfg_date", requires=["mfg_date"])
def check_r4(context):
    """
    R4: Manufacturing Date format.
    """
    raw_date = context["extraction"]["fields"]["mfg_date"]["raw"].upper()
    config = context.get("config", {})
    r4_config = config.get("r4", {})
    
    # Strip prefixes
    for prefix in r4_config.get("prefixes", []):
        raw_date = raw_date.replace(prefix, "").strip()
        
    # Also strip common separators
    raw_date = raw_date.strip(" :.-")
    
    # We can try parsing with all formats
    matched = False
    for fmt in r4_config.get("date_formats", []):
        try:
            # We want exact match for the format. We can use datetime.strptime
            datetime.strptime(raw_date, fmt)
            matched = True
            break
        except ValueError:
            pass
            
    if matched:
        return {"status": "PASS"}
    else:
        fix = r4_config.get("fixes", {}).get("invalid", "valid formats")
        return {"status": "FAIL", "fix": fix}
