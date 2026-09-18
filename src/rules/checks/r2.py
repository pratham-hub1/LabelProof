from src.rules.engine import registry

@registry.register("r2_generic_name", requires=[])
def check_r2(context):
    """
    R2: Common/Generic Name of the commodity.
    Presence check: if VERIFIED (handled by engine dependencies), PASS.
    Wait, the engine will not call this if it's ABSENT. 
    But if it's ABSENT, it returns NA with DEPENDENCY_UNAVAILABLE. 
    However, R2's goal IS to check presence! 
    F3 3.3 says: "Presence check: if VERIFIED, PASS. Otherwise NA with fix 'print the commodity's common/generic name'."
    But if we use requires=["generic_name"], the engine intercepts ABSENT and returns NA DEPENDENCY_UNAVAILABLE.
    So R2 wouldn't get a chance to return its specific fix.
    Let's register without `requires` or handle it.
    If we register without requires, we can check the status ourselves.
    """
    field_status = context.get("field_status", {})
    status = field_status.get("generic_name")
    
    if status == "VERIFIED":
        return {"status": "PASS"}
        
    config = context.get("config", {})
    fix = config.get("r2", {}).get("fixes", {}).get("missing", "print the commodity's common/generic name")
    
    # If not VERIFIED, it's missing or unreadable
    return {"status": "FAIL", "fix": fix}
