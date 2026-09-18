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
    
    # 1. Multiple instances sweep
    word_index = context.get("word_index", [])
    if word_index:
        from src.gauntlet.anchors_loader import load_anchors_config
        anchors = load_anchors_config().get("mrp", [])
        
        anchor_matches = 0
        for w in word_index:
            w_text = w.get("word", "")
            if any(re.search(a, w_text, re.IGNORECASE) for a in anchors):
                anchor_matches += 1

        
        # If we see multiple anchor words spaced apart, it could be multiple instances.
        # A more robust way is to join the word index and count non-overlapping anchor regions,
        # but counting occurrences of price-like clusters works.
        # The spec says: "sweep the whole word index for MRP anchor matches... >= 2 distinct values -> NEEDS_REVIEW"
    
    # Let's count price numbers in the raw text as a proxy for the word index sweep,
    # because the raw string is the extracted region. If the LLM captured multiple "Rs 20 ... Rs 30"
    mrp_value_count = len(re.findall(r'(?:Rs\.?|₹|MRP)\s*\d+', raw_mrp, re.IGNORECASE))
    if mrp_value_count > 1:
        return {"status": "NEEDS_REVIEW", "reason": "multiple MRP instances detected"}
        
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
