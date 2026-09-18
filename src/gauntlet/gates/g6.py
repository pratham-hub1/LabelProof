def check_g6(claim, word_index=None, image_meta=None):
    """
    G6: Confidence gate
    Self-reported confidence >= 0.60
    """
    if not isinstance(claim, dict):
        return False
        
    required_keys = ["raw", "parsed", "confidence", "box"]
    for k in required_keys:
        if k not in claim:
            return False
            
    conf = claim["confidence"]
    if conf is None:
        return False
        
    try:
        conf = float(conf)
    except (ValueError, TypeError):
        return False
        
    return conf >= 0.60
