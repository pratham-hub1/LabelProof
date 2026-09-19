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
    parsed_date = None
    for fmt in r4_config.get("date_formats", []):
        try:
            # We want exact match for the format. We can use datetime.strptime
            parsed_date = datetime.strptime(raw_date, fmt)
            matched = True
            break
        except ValueError:
            pass
            
    if matched:
        # N-B8 fix: use record_time instead of wall-clock
        record_time_iso = context.get("scan_fields", {}).get("created_at")
        if record_time_iso:
            record_time = datetime.fromisoformat(record_time_iso.replace("Z", "+00:00")).replace(tzinfo=None)
        else:
            record_time = datetime.now()
            
        if parsed_date > record_time:
            return {"status": "NEEDS_REVIEW", "reason": "manufacturing date is in the future"}
        return {"status": "PASS"}
    else:
        fix = r4_config.get("fixes", {}).get("invalid", "valid formats")
        return {"status": "FAIL", "fix": fix}
