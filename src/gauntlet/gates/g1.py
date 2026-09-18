def check_g1(claim, word_index=None, image_meta=None):
    """
    G1: Box sanity
    Checks if the claimed box is non-degenerate and inside image bounds.
    """
    if not claim or "box" not in claim or claim["box"] is None:
        return False
        
    box = claim["box"]
    if len(box) != 4:
        return False
        
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    
    if width <= 0 or height <= 0:
        return False
        
    if image_meta and "width" in image_meta and "height" in image_meta:
        img_w = image_meta["width"]
        img_h = image_meta["height"]
        
        # Check if box is completely outside or degenerate relative to image
        if left >= img_w or top >= img_h:
            return False
            
        if right <= 0 or bottom <= 0:
            return False
            
    return True
