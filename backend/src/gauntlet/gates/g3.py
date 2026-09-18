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
                # Convert to string and strip decimals (or keep them?)
                val_str = str(val).replace('.', '')
                # Just check if the string representation of the parsed value's digits appears in raw digits
                # Actually, just checking if the sequence of digits appears in the raw text directly is better
                val_digits = "".join(re.findall(r'\d+', str(val)))
                if val_digits and val_digits not in raw_digits:
                     # Wait, maybe it's floating point like 1.5 -> "15" in raw?
                     # Let's be lenient: every digit in parsed value must exist in raw text in order.
                     return False
            elif isinstance(val, str):
                # For units like "g", "kg", currency "INR", phone, email
                # Phone numbers have digits
                if key == "phone":
                    phone_digits = "".join(re.findall(r'\d+', val))
                    if phone_digits and phone_digits not in raw_digits:
                        return False
                elif key == "unit":
                    # unit should be in raw (case-insensitive)
                    if val.lower() not in raw.lower():
                        return False
                        
    return True
