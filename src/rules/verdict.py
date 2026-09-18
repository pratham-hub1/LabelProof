def final_verdict(field_statuses, check_results):
    """
    Computes the final terminal state of the scan.
    Returns one of: DONE, NEEDS_REVIEW, FAILED
    """
    # 1. Check for FAIL conditions
    for field, status in field_statuses.items():
        if status == "ABSENT":
            return "FAILED"
            
    for rule_id, result in check_results.items():
        if result["status"] == "FAIL":
            return "FAILED"
            
    # 2. Check for NEEDS_REVIEW conditions
    for field, status in field_statuses.items():
        if status in ["NEEDS_REVIEW", "UNREADABLE"]:
            return "NEEDS_REVIEW"
            
    for rule_id, result in check_results.items():
        if result["status"] == "NEEDS_REVIEW":
            return "NEEDS_REVIEW"
            
    # 3. Otherwise DONE
    return "DONE"
