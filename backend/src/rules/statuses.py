def resolve_field_statuses(gauntlet_results, readability, exemptions=None):
    """
    Resolves the gauntlet results into the standard field_status map.
    gauntlet_results: dict of field -> {"gauntlet_status": ..., "reason_code": ...}
    exemptions: dict from evaluate_exemptions (e.g., {"status": "EXEMPT", "reason": None})
    """
    field_status_map = {}
    
    exempt_status = exemptions.get("status") if isinstance(exemptions, dict) else exemptions
    
    for field, res in gauntlet_results.items():
        if exempt_status == "EXEMPT":
            field_status_map[field] = "NA_EXEMPT"
            continue
            
        g_status = res.get("gauntlet_status")
        reason = res.get("reason_code")
        
        if g_status == "VERIFIED":
            field_status_map[field] = "VERIFIED"
        elif g_status == "NEEDS_REVIEW":
            field_status_map[field] = "NEEDS_REVIEW"
        elif g_status == "ABSENT":
            if reason == "NOT_PRINTED":
                field_status_map[field] = "ABSENT"
            elif reason == "UNREADABLE_IMAGE":
                field_status_map[field] = "UNREADABLE"
            else:
                field_status_map[field] = "NEEDS_REVIEW"
        elif g_status == "NA":
            # Some gauntlet implementations might use NA or ABSENT. F1 table says "NA - reason: NOT_PRINTED"
            if reason == "UNREADABLE_IMAGE":
                field_status_map[field] = "UNREADABLE"
            elif reason == "NOT_PRINTED":
                field_status_map[field] = "ABSENT"
            elif reason in ["VERIFY_FAILED", "UNSUPPORTED_LANGUAGE"]:
                field_status_map[field] = "NEEDS_REVIEW"
            else:
                field_status_map[field] = "NEEDS_REVIEW"
        elif g_status == "UNREADABLE":
             field_status_map[field] = "UNREADABLE"
        else:
             field_status_map[field] = "NEEDS_REVIEW"
             
    return field_status_map
