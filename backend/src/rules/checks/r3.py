from src.rules.engine import registry

@registry.register("r3_net_quantity", requires=["net_quantity"])
def check_r3(context):
    """
    R3: Net Quantity format and legal unit.
    """
    nq = context["extraction"]["fields"]["net_quantity"]
    parsed = nq.get("parsed")
    
    if not parsed or not parsed.get("unit"):
        return {"status": "FAIL", "fix": "print standard unit (e.g. g, ml, pcs)"}
        
    unit = parsed.get("unit", "").lower()
    if unit in ["g", "kg", "ml", "l", "pcs"]:
        return {"status": "PASS"}
    else:
        return {"status": "FAIL", "fix": "print standard unit (e.g. g, ml, pcs)"}
