from src.rules.engine import registry

@registry.register("r2_generic_name", requires=["generic_name"])
def check_r2(context):
    """
    R2: Common/Generic Name of the commodity.
    Presence check: if VERIFIED (handled by engine dependencies), PASS.
    """
    field_status = context.get("field_status", {})
    status = field_status.get("generic_name")
    
    if status == "VERIFIED":
        raw = context.get("extraction", {}).get("fields", {}).get("generic_name", {}).get("raw")
        if not raw:
            return {"status": "NA", "reason_code": "DEPENDENCY_UNAVAILABLE", "message": "Missing generic_name text"}
        return {"status": "PASS"}
        
    if status == "ABSENT":
        config = context.get("config", {})
        fix = config.get("r2", {}).get("fixes", {}).get("missing", "print the commodity's common/generic name")
        return {"status": "FAIL", "fix": fix}
        
    # Should not be reached if engine properly short-circuits
    return {"status": "NEEDS_REVIEW", "reason": "unexpected status"}
