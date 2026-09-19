from src.rules.engine import registry

@registry.register("r3_net_quantity", requires=["net_quantity"])
def check_r3(context):
    """
    R3: Net Quantity format and legal unit.
    """
    nq = context.get("extraction", {}).get("fields", {}).get("net_quantity", {})
    parsed = nq.get("parsed")
    
    if not parsed or not parsed.get("unit") or parsed.get("value") is None:
        return {"status": "FAIL", "fix": "print standard unit (e.g. g, ml, pcs)"}
        
    unit = parsed.get("unit", "").lower()
    val = parsed.get("value")
    
    if val < 1 and unit in ["kg", "l"]:
        return {"status": "FAIL", "fix": "<1 kg must be grams / <1 L must be ml"}
        
    if unit in ["g", "kg", "ml", "l", "pcs"]:
        return {"status": "PASS"}
    else:
        return {"status": "FAIL", "fix": "print standard unit (e.g. g, ml, pcs)"}
