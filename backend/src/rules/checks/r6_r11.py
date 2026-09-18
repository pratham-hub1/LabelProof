from src.rules.engine import registry

@registry.register("r6_consumer_care", requires=[])
def check_r6(context):
    """
    R6: Consumer Care presence.
    """
    field_status = context.get("field_status", {})
    status = field_status.get("consumer_care")
    
    if status == "VERIFIED":
        return {"status": "PASS"}
        
    config = context.get("config", {})
    fix = config.get("r6", {}).get("fixes", {}).get("no_contact", "no contactable channel")
    
    return {"status": "FAIL", "fix": fix}

@registry.register("r11_qualifiers", requires=["net_quantity"])
def check_r11(context):
    """
    R11: No misleading qualifiers unless Third Schedule.
    """
    extraction = context.get("extraction", {})
    fields = extraction.get("fields", {})
    
    nq_raw = fields.get("net_quantity", {}).get("raw", "") or ""
    gn_raw = fields.get("generic_name", {}).get("raw", "") or ""
    
    config = context.get("config", {})
    r11_config = config.get("r11", {})
    
    third_schedule = r11_config.get("third_schedule", [])
    
    gn_lower = gn_raw.lower()
    if gn_lower and any(item.lower() in gn_lower for item in third_schedule):
        return {"status": "PASS"}
        
    qualifiers = r11_config.get("qualifiers", [])
    import re
    
    text_to_check = (nq_raw + " " + gn_raw).lower()
    for q in qualifiers:
        # Require the qualifier to be followed by a quantity word or number
        # e.g., "about 200g", "about net wt"
        pattern = r'\b' + re.escape(q.lower()) + r'\b\s*(?:net|wt|weight|volume|content|[\d\.])'
        if re.search(pattern, text_to_check):
            fix = r11_config.get("fixes", {}).get("misleading", "misleading qualifier present")
            return {"status": "FAIL", "fix": fix}
            
    return {"status": "PASS"}
