from src.rules.engine import registry
import unicodedata

@registry.register("r7_language", requires=[])
def check_r7(context):
    """
    R7: Language. Declarations in Hindi (Devanagari) or English.
    """
    extraction = context.get("extraction", {})
    fields = extraction.get("fields", {})
    field_status = context.get("field_status", {})
    
    for field_name, status in field_status.items():
        if status != "VERIFIED":
            continue
            
        raw = fields.get(field_name, {}).get("raw", "")
        if not raw:
            continue
            
        filtered = "".join(c for c in raw if not unicodedata.category(c).startswith(('P', 'N', 'S', 'Z')))
        if not filtered:
            continue
            
        devanagari_count = 0
        latin_count = 0
        for c in filtered:
            if 0x0900 <= ord(c) <= 0x097F:
                devanagari_count += 1
            elif 0x0041 <= ord(c) <= 0x005A or 0x0061 <= ord(c) <= 0x007A or 0x00C0 <= ord(c) <= 0x024F:
                latin_count += 1
                
        threshold = len(filtered) / 2
        
        if devanagari_count > threshold and latin_count <= threshold:
            return {"status": "NEEDS_REVIEW", "reason": "Hindi-only label", "reason_code": "UNSUPPORTED_LANGUAGE"}
            
        if devanagari_count <= threshold and latin_count <= threshold:
            config = context.get("config", {})
            fix = config.get("r7", {}).get("fixes", {}).get("wrong_language", "Use Hindi or English")
            return {"status": "FAIL", "fix": fix}
            
    return {"status": "PASS"}
