import re
from src.rules.engine import registry

@registry.register("r5_mrp", requires=["mrp"])
def check_r5(context):
    """
    R5: MRP format and taxes clause.
    """
    raw_mrp = context["extraction"]["fields"]["mrp"]["raw"]
    config = context.get("config", {})
    r5_config = config.get("r5", {})
    
    # Check multiple MRPs
    # Simple heuristic: if we see "Rs." or "₹" or digits multiple times in distinct clusters.
    # Actually, a simpler way is checking if "Rs" or "MRP" or currency symbol appears more than once.
    # Let's count "Rs", "Rs.", "₹"
    rs_count = len(re.findall(r'(?i)\bRs\.?\b|₹', raw_mrp))
    mrp_count = len(re.findall(r'(?i)\bMRP\b', raw_mrp))
    if rs_count > 1 or mrp_count > 1:
        # Actually F3 3.3 says "multiple MRP instances (if we see Rs. X... Rs. Y in the same raw string) -> FAIL"
        # We'll just check if multiple numbers exist with Rs.
        return {"status": "FAIL", "fix": r5_config.get("fixes", {}).get("missing_taxes", "taxes clause is unambiguous in law")}
        
    taxes_clauses = r5_config.get("taxes_clauses", [])
    has_taxes = any(clause.lower() in raw_mrp.lower() for clause in taxes_clauses)
    
    if has_taxes:
        return {"status": "PASS"}
    else:
        fix = r5_config.get("fixes", {}).get("missing_taxes", "taxes clause is unambiguous in law")
        return {"status": "FAIL", "fix": fix}
