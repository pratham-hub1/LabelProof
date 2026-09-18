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
    left = box["left"]
    top = box["top"]
    right = left + box["width"]
    bottom = top + box["height"]
    
    inside_words = []
    for w in word_index:
        wb = w["box"]
        cx = wb["left"] + wb["width"] / 2.0
        cy = wb["top"] + wb["height"] / 2.0
        
        if left <= cx <= right and top <= cy <= bottom:
            inside_words.append(w)
            
    inside_words.sort(key=lambda x: (x["box"]["top"], x["box"]["left"]))
    ocr_text = " ".join(w["word"] for w in inside_words)
    
    # Check if any anchor regex matches the OCR text inside the box
    for anchor_pattern in field_anchors:
        if re.search(anchor_pattern, ocr_text, re.IGNORECASE):
            return True
            
    return False
