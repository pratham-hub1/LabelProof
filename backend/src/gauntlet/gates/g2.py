def check_g2(claim, word_index=None, image_meta=None):
    """
    G2: Raw text non-empty
    Checks if the claimed raw text is non-empty.
    """
    if not claim or "raw" not in claim:
        return False
        
    raw = claim["raw"]
    if raw is None:
        return False
        
    if isinstance(raw, str) and not raw.strip():
        return False
        
    return True
