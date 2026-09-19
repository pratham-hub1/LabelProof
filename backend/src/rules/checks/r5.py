import re
from src.rules.engine import registry

@registry.register("r5_mrp", requires=["mrp"])
def check_r5(context):
    """
    R5: MRP format and taxes clause.
    """
    raw_mrp = context.get("extraction", {}).get("fields", {}).get("mrp", {}).get("raw")
    if not raw_mrp:
        return {"status": "NA", "reason_code": "DEPENDENCY_UNAVAILABLE", "message": "Missing mrp text"}
    config = context.get("config", {})
    r5_config = config.get("r5", {})
    
    # 1. Multiple instances sweep
    word_index = context.get("extraction", {}).get("word_index", [])
    
    from src.gauntlet.anchors_loader import load_anchors_config
    mrp_anchors = load_anchors_config().get("mrp", [])
    
    # Combine anchors into one regex, adding common price prefixes like Rs.
    anchors_regex = "|".join(mrp_anchors + [r"Rs\.?", r",1"])
    
    if word_index:
        full_text = " ".join([w.get("word", "") for w in word_index])
        
        # Look for numbers following any MRP anchor anywhere in the label
        prices = re.findall(rf'(?:{anchors_regex})\s*(\d+(?:\.\d{{1,2}})?)', full_text, re.IGNORECASE)
        
        # Deduplicate values
        distinct_prices = set(float(p) for p in prices if p)
        if len(distinct_prices) > 1:
            return {"status": "NEEDS_REVIEW", "reason": "multiple distinct MRP values detected"}
    else:
        # Fallback if no word index
        prices = re.findall(rf'(?:{anchors_regex})\s*(\d+(?:\.\d{{1,2}})?)', raw_mrp, re.IGNORECASE)
        if len(set(float(p) for p in prices if p)) > 1:
            return {"status": "NEEDS_REVIEW", "reason": "multiple distinct MRP values detected"}
        
    # 2. Shorthand check
    # Check if 'Maximum Retail Price' is present, otherwise it's shorthand 'MRP'
    has_full_mrp = bool(re.search(r'\bMaximum Retail Price\b', raw_mrp, re.IGNORECASE))
    
    # Check taxes
    taxes_clauses = r5_config.get("taxes_clauses", [])
    has_full_taxes = any(clause.lower() in raw_mrp.lower() for clause in taxes_clauses if "incl." not in clause.lower())
    has_shorthand_taxes = any("incl." in clause.lower() and clause.lower() in raw_mrp.lower() for clause in taxes_clauses)
    
    if not has_full_taxes and not has_shorthand_taxes:
        fix = r5_config.get("fixes", {}).get("missing_taxes", "taxes clause is unambiguous in law")
        return {"status": "FAIL", "fix": fix}
        
    if not has_full_mrp or has_shorthand_taxes:
        return {"status": "NEEDS_REVIEW", "reason": "shorthand MRP or taxes clause"}
        
    return {"status": "PASS"}
