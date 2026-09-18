import numpy as np

def _boxes_intersect(b1, b2):
    return not (b1["left"] >= b2["left"] + b2["width"] or 
                b1["left"] + b1["width"] <= b2["left"] or 
                b1["top"] >= b2["top"] + b2["height"] or 
                b1["top"] + b1["height"] <= b2["top"])

def check_r9(word_index, quantity_box, h_px, ink_map, ink_threshold=0.05):
    """
    Evaluates R9 (clear space).
    """
    left = quantity_box["left"] - 2 * h_px
    right = quantity_box["left"] + quantity_box["width"] + 2 * h_px
    top = quantity_box["top"] - 1 * h_px
    bottom = quantity_box["top"] + quantity_box["height"] + 1 * h_px
    
    zone_box = {
        "left": left,
        "top": top,
        "width": right - left,
        "height": bottom - top
    }
    
    # Check word index
    for word in word_index:
        # Ignore words that are inside the quantity_box (they are the declaration itself)
        # We consider a word part of the declaration if its box intersects heavily or is mostly inside.
        # Simple check: if its center is inside the quantity box, ignore it.
        cx = word["box"]["left"] + word["box"]["width"] / 2.0
        cy = word["box"]["top"] + word["box"]["height"] / 2.0
        
        in_quantity = (quantity_box["left"] <= cx <= quantity_box["left"] + quantity_box["width"] and
                       quantity_box["top"] <= cy <= quantity_box["top"] + quantity_box["height"])
                       
        if not in_quantity and _boxes_intersect(word["box"], zone_box):
            return {"status": "FAIL", "reason": "printed information too close"}
            
    # Check ink coverage
    if ink_map is not None:
        # ink_map is expected to be a binary numpy array (True for ink, False for bg)
        # Clip coordinates to image bounds
        img_h, img_w = ink_map.shape
        z_left = max(0, int(left))
        z_right = min(img_w, int(right))
        z_top = max(0, int(top))
        z_bottom = min(img_h, int(bottom))
        
        q_left = max(0, int(quantity_box["left"]))
        q_right = min(img_w, int(quantity_box["left"] + quantity_box["width"]))
        q_top = max(0, int(quantity_box["top"]))
        q_bottom = min(img_h, int(quantity_box["top"] + quantity_box["height"]))
        
        # Calculate area of the zone excluding the quantity box
        zone_area = (z_right - z_left) * (z_bottom - z_top)
        q_area_in_zone = max(0, q_right - max(z_left, q_left)) * max(0, q_bottom - max(z_top, q_top))
        effective_area = zone_area - q_area_in_zone
        
        if effective_area > 0:
            zone_ink = np.sum(ink_map[z_top:z_bottom, z_left:z_right])
            q_ink = np.sum(ink_map[q_top:q_bottom, q_left:q_right])
            non_text_ink = max(0, zone_ink - q_ink)
            
            density = non_text_ink / effective_area
            if density > ink_threshold:
                return {"status": "FAIL", "reason": "printed information too close"}
                
    return {"status": "PASS"}
