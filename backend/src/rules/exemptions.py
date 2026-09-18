def evaluate_exemptions(gauntlet_output, tobacco_config):
    """
    Evaluates if the label is exempt (small package rule) or Chapter II inapplicable.
    Returns:
    {"status": "EXEMPT", "reason": None}
    {"status": "NEEDS_REVIEW", "reason": "...reason string..."}
    {"status": "NONE", "reason": None}
    """
    fields = gauntlet_output
    
    nq = fields.get("net_quantity", {})
    if nq.get("gauntlet_status") != "VERIFIED":
        return {"status": "NONE", "reason": None}
        
    parsed = nq.get("parsed", {})
    if not parsed or parsed.get("value") is None:
        return {"status": "NONE", "reason": None}
        
    unit = parsed.get("unit", "").lower()
    val = parsed.get("value")
    
    # Convert to canonical g/ml
    # Reusing R3 units logic
    if unit in ["kg", "l"]:
        val_g_ml = val * 1000
    elif unit in ["g", "ml"]:
        val_g_ml = val
    else:
        return {"status": "NONE", "reason": None}
        
    # Check > 25 kg/l
    if val_g_ml > 25000:
        return {"status": "NEEDS_REVIEW", "reason": "Chapter II likely inapplicable; cement/fertilizer exception cannot be ruled out"}
        
    # Check <= 10 g/ml
    if val_g_ml <= 10:
        gn = fields.get("generic_name", {})
        if gn.get("gauntlet_status") != "VERIFIED":
            return {"status": "NEEDS_REVIEW", "reason": "exemption uncertain: commodity type unverified"}
            
        gn_raw = gn.get("raw", "").lower()
        import re
        for kw in tobacco_config.get("tobacco_keywords", []):
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', gn_raw):
                return {"status": "NEEDS_REVIEW", "reason": "exemption uncertain: tobacco proviso"}
                
        return {"status": "EXEMPT", "reason": None}
        
    return {"status": "NONE", "reason": None}
