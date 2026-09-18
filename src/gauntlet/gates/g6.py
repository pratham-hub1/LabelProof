def check_g6(claim, word_index=None, image_meta=None):
    """
    G6: Confidence gate
    Self-reported confidence >= 0.60
    """
    if not claim or "confidence" not in claim:
        return False
        
    conf = claim["confidence"]
    if conf is None:
        return False
        
    try:
        conf = float(conf)
    except ValueError:
        return False
        
    return conf >= 0.60
