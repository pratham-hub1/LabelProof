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
    
    if not has_pin and not has_state:
        return {"status": "FAIL", "fix": r1_config.get("fixes", {}).get("street_missing", "street-level detail missing")}
    elif not has_pin or not has_state:
        # One present -> NEEDS_REVIEW
        return {"status": "NEEDS_REVIEW", "reason": "address completeness ambiguous"}
    else:
        return {"status": "PASS"}
