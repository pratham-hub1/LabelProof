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
        
    if isinstance(box, dict):
        left, top = box.get("left", 0), box.get("top", 0)
        right, bottom = left + box.get("width", 0), top + box.get("height", 0)
    else:
        left, top, right, bottom = box
    width = right - left
    height = bottom - top
    
    if width <= 0 or height <= 0:
        print(f"G1 FAIL: width={width}, height={height}")
        return False
        
    if image_meta and "width" in image_meta and "height" in image_meta:
        img_w = image_meta["width"]
        img_h = image_meta["height"]
        
        # Check if box is completely or partially outside bounds
        if left < 0 or top < 0:
            print(f"G1 FAIL: left={left}, top={top}")
            return False
            
        if right > img_w or bottom > img_h:
            print(f"G1 FAIL: right={right} > {img_w} OR bottom={bottom} > {img_h}")
            return False
            
    return True
