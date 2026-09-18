def check_g1(claim, word_index=None, image_meta=None):
    """
    G1: Box sanity
    Checks if the claimed box is non-degenerate and inside image bounds.
    """
    if not claim or "box" not in claim or claim["box"] is None:
        return False
        
    box = claim["box"]
    if not all(k in box for k in ["left", "top", "width", "height"]):
        return False
        
    if box["width"] <= 0 or box["height"] <= 0:
        return False
        
    if image_meta and "width" in image_meta and "height" in image_meta:
        img_w = image_meta["width"]
        img_h = image_meta["height"]
        
        # Check if box is completely or partially outside
        if box["left"] < 0 or box["top"] < 0:
            return False
            
        if box["left"] + box["width"] > img_w or box["top"] + box["height"] > img_h:
            return False
            
    return True
