def evaluate_exemptions(gauntlet_output, tobacco_config):
    """
    Evaluates if the label is exempt (small package rule) or Chapter II inapplicable.
    Returns:
    {"applied": True, "citation": "Rule 26(a)", "reason": "Rule 26(a) exemption, quantity <=10 g/ml verified", "status_override": "EXEMPT"}
    {"applied": False, "citation": "Rule 26(a) proviso (amendment)", "reason": "...reason string...", "status_override": "NEEDS_REVIEW"}
    {"applied": False, "citation": None, "reason": None, "status_override": "NONE"}
    """
    fields = gauntlet_output
    
    nq = fields.get("net_quantity", {})
    if nq.get("gauntlet_status") != "VERIFIED":
        return {"applied": False, "citation": None, "reason": None, "status_override": "NONE"}
        
    parsed = nq.get("parsed", {})
    if not parsed or parsed.get("value") is None:
        return {"applied": False, "citation": None, "reason": None, "status_override": "NONE"}
        
    unit = parsed.get("unit", "").lower()
    val = parsed.get("value")
    
    # Convert to canonical g/ml
    # Reusing R3 units logic
    if unit in ["kg", "l"]:
        val_g_ml = val * 1000
    elif unit in ["g", "ml"]:
        val_g_ml = val
    else:
        return {"applied": False, "citation": None, "reason": None, "status_override": "NONE"}
        
    # Check > 25 kg/l
    if val_g_ml > 25000:
        return {"applied": False, "citation": "Rule 3(a)", "reason": "Chapter II likely inapplicable; cement/fertilizer exception cannot be ruled out", "status_override": "NEEDS_REVIEW"}
        
    # Check <= 10 g/ml
    if val_g_ml <= 10:
        gn = fields.get("generic_name", {})
        if gn.get("gauntlet_status") != "VERIFIED":
            return {"applied": False, "citation": "Rule 26(a) proviso (amendment)", "reason": "exemption uncertain: commodity type unverified", "status_override": "NEEDS_REVIEW"}
            
        gn_raw = gn.get("raw", "").lower()
        import re
        for kw in tobacco_config.get("tobacco_keywords", []):
            if re.search(r'\b' + re.escape(kw.lower()) + r'\b', gn_raw):
                return {"applied": False, "citation": "Rule 26(a) proviso (amendment)", "reason": "exemption uncertain: tobacco proviso", "status_override": "NEEDS_REVIEW"}
                
        return {"applied": True, "citation": "Rule 26(a)", "reason": "Rule 26(a) exemption, quantity <=10 g/ml verified", "status_override": "EXEMPT"}
        
    return {"applied": False, "citation": None, "reason": None, "status_override": "NONE"}

