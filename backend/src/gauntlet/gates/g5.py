import re

def check_g5(claim, field_name, word_index, anchors_config, image_meta=None):
    """
    G5: Anchor check
    The claimed box must contain an OCR-detected keyword anchor of the right field type.
    """
    if not claim or "box" not in claim or claim["box"] is None:
        return False
        
    if not anchors_config or field_name not in anchors_config:
        # Unanchored field -> G5 trivially passes
        return True
        
    field_anchors = anchors_config[field_name]
    if not field_anchors:
        return True
        
    box = claim["box"]
    
    # Get all words inside the box
    # We can reuse get_words_in_box from g4, but let's just do it directly or assume it's passed.
    # To keep it independent:
    if isinstance(box, dict):
        left, top = box.get("left", 0), box.get("top", 0)
        right, bottom = left + box.get("width", 0), top + box.get("height", 0)
    else:
        left, top, right, bottom = box
    
    # We'll just check if any anchor matches any word inside the box.
    inside_words = []
    for w in word_index:
        wb = w["box"]
        if isinstance(wb, dict):
            w_left, w_top = wb.get("left", 0), wb.get("top", 0)
            w_right, w_bottom = w_left + wb.get("width", 0), w_top + wb.get("height", 0)
        else:
            w_left, w_top, w_right, w_bottom = wb
        cx = (w_left + w_right) / 2.0
        cy = (w_top + w_bottom) / 2.0
        
        if left <= cx <= right and top <= cy <= bottom:
            inside_words.append(w)
            
    def get_top_left(x):
        b = x["box"]
        if isinstance(b, dict):
            return b.get("top", 0), b.get("left", 0)
        return b[1], b[0]
    inside_words.sort(key=get_top_left)
    ocr_text = " ".join(w["word"] for w in inside_words)
    
    # Check if any anchor regex matches the OCR text inside the box
    for anchor_pattern in field_anchors:
        if re.search(anchor_pattern, ocr_text, re.IGNORECASE):
            return True
            
    return False
