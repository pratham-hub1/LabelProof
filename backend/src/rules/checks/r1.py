import re
from src.rules.engine import registry

@registry.register("r1_manufacturer_details", requires=["manufacturer_name", "manufacturer_address"])
def check_r1(context):
    """
    R1: Manufacturer Name and Address presence and completeness.
    """
    field_status = context.get("field_status", {})
    if field_status.get("manufacturer_name") == "ABSENT":
        return {"status": "FAIL", "fix": "manufacturer name not found on label"}
    if field_status.get("manufacturer_address") == "ABSENT":
        return {"status": "FAIL", "fix": "print the manufacturer's name and address"}
        
    address = context["extraction"]["fields"]["manufacturer_address"]["raw"]
        
    config = context.get("config", {})
    r1_config = config.get("r1", {})
    
    # Defense 1: PIN code
    pin_regex = r1_config.get("pin_regex", r"\b\d{6}\b")
    has_pin = bool(re.search(pin_regex, address))
    
    # Defense 2: State name
    states = r1_config.get("states", [])
    has_state = any(state.lower() in address.lower() for state in states)
    
    # Defense 3: City pattern (approximate) or dilated-box region analysis
    has_city = bool(re.search(r'\b[A-Z][a-z]{3,}\b,\s*[A-Z]', address)) # rudimentary pattern
    
    # Documented dilated-box region check
    has_region = False
    addr_box = context["extraction"]["fields"]["manufacturer_address"].get("box")
    word_index = context.get("extraction", {}).get("word_index", [])
    if addr_box and word_index:
        left, top, right, bottom = addr_box
        w, h = right - left, bottom - top
        # Dilate by 1.5x
        dl, dt, dr, db = left - 0.5*w, top - 0.5*h, right + 0.5*w, bottom + 0.5*h
        words_in_region = 0
        for word in word_index:
            wl, wt, wr, wb = word["box"]
            cx, cy = (wl + wr) / 2, (wt + wb) / 2
            if dl <= cx <= dr and dt <= cy <= db:
                words_in_region += 1
        has_region = words_in_region >= 4
    else:
        # Fallback to word count if no box/index available
        has_region = len(address.split()) >= 4
    
    if has_pin and has_state:
        return {"status": "PASS"}
    elif has_pin or has_state or has_city or has_region:
        return {"status": "NEEDS_REVIEW", "reason": "address completeness ambiguous"}
    else:
        return {"status": "FAIL", "fix": r1_config.get("fixes", {}).get("street_missing", "print the manufacturer's name and address")}
