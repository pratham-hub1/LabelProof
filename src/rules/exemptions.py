def evaluate_exemptions(extraction):
    """
    Evaluates if the label is exempt (small package rule).
    <= 10g, <= 10ml, or <= Rs. 10
    """
    fields = extraction.get("fields", {})
    
    # Check MRP
    mrp_field = fields.get("mrp", {})
    if mrp_field:
        parsed = mrp_field.get("parsed")
        if parsed and parsed.get("value") is not None:
            if parsed["value"] <= 10:
                return "EXEMPT"
                
    # Check Net Quantity
    nq_field = fields.get("net_quantity", {})
    if nq_field:
        parsed = nq_field.get("parsed")
        if parsed and parsed.get("value") is not None:
            unit = parsed.get("unit", "").lower()
            val = parsed["value"]
            if unit in ["g", "ml"] and val <= 10:
                return "EXEMPT"
                
    return "NONE"
