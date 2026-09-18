import re

def check_g3(claim, word_index=None, image_meta=None):
    """
    G3: Parsed <-> raw consistency
    Checks if the digits of parsed values appear in raw, and if unit tokens are present.
    """
    if not claim or "raw" not in claim or not claim["raw"]:
        return False
        
    raw = claim["raw"]
    parsed = claim.get("parsed")
    
    if parsed is None:
        return True # Nothing to check
        
    # Check digits for generic numerical values
    # Extract all digits from raw text
    raw_digits = "".join(re.findall(r'\d+', raw))
    
    # Check values in parsed
    if isinstance(parsed, dict):
        for key, val in parsed.items():
            if val is None:
                continue
            if isinstance(val, (int, float)):
                val_str = str(val)
                if val_str.endswith(".0"):
                    val_str = val_str[:-2]
                val_digits = "".join(re.findall(r'\d+', val_str))
                if val_digits:
                    # Must appear contiguously (optionally separated by . or ,) and bounded by non-digits
                    pattern = r'(?<!\d)' + r'[.,]?'.join(list(val_digits)) + r'(?!\d)'
                    if not re.search(pattern, raw):
                        return False
            elif isinstance(val, str):
                if key == "phone":
                    phone_digits = "".join(re.findall(r'\d+', val))
                    if phone_digits:
                        pattern = r'(?<!\d)' + r'[-\s.,]?'.join(list(phone_digits)) + r'(?!\d)'
                        if not re.search(pattern, raw):
                            return False
                elif key == "unit":
                    # unit should be in raw as a distinct word or attached to digits
                    # e.g., "g" inside "200g" or "200 g". It should not match "g" inside "good"
                    # so (?<=\d|\s|^) unit (?=\s|$)
                    # Actually, word boundaries \b work if there's a space, but for "200g", there is no \b between 0 and g.
                    # Let's use a regex that allows a digit or non-word char before, and a non-word char after.
                    pattern = r'(?:^|\b|\d)' + re.escape(val.lower()) + r'(?:\b|$)'
                    if not re.search(pattern, raw.lower()):
                        return False
                        
    return True
