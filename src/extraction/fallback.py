def needs_fallback(extraction_data):
    """
    Returns True if the extraction needs to fallback to Sonnet.
    Trigger rule (G0 code-side):
    - G0 schema-fail (handled by raising/catching an exception before this) OR
    - >= 2 of the 7 declaration fields with confidence < 0.60
    """
    # Assuming extraction_data is schema-valid
    fields = extraction_data.get("fields", {})
    
    weak_count = 0
    for field_name in ["manufacturer_name", "manufacturer_address", "generic_name", 
                       "net_quantity", "mfg_date", "mrp", "consumer_care"]:
        field_data = fields.get(field_name, {})
        # If confidence is null (field not printed), what does that mean?
        # A not-printed field might have a null confidence. F1's confidence gate handles missing.
        # But wait, if confidence is None, does it count as < 0.60?
        # F9 says: ">= 2 fields < 0.60". If it's missing, confidence is None. We only count printed fields?
        # F9: ">=2 of the 7 declaration fields with confidence < 0.60 -> ONE Sonnet retry"
        # Let's count None as < 0.60 or just skip None? 
        # Actually, if the LLM couldn't find the field, it returns None. That is a weak field.
        conf = field_data.get("confidence")
        if conf is None or conf < 0.60:
            weak_count += 1
            
    return weak_count >= 2
