import json
import os
import re

from src.gauntlet.gates.g1 import check_g1
from src.gauntlet.gates.g2 import check_g2
from src.gauntlet.gates.g3 import check_g3
from src.gauntlet.gates.g4 import check_g4
from src.gauntlet.gates.g5 import check_g5
from src.gauntlet.gates.g6 import check_g6

def load_reasons_config(config_path=None):
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "reasons.config")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def has_field_anchor(field_name, word_index, anchors_config):
    if not anchors_config or field_name not in anchors_config:
        return False
        
    field_anchors = anchors_config[field_name]
    if not field_anchors:
        return False
        
    ocr_text = " ".join(w["word"] for w in word_index)
    for anchor_pattern in field_anchors:
        if re.search(anchor_pattern, ocr_text, re.IGNORECASE):
            return True
    return False

def is_devanagari_only(text):
    if not text:
        return False
    
    # Strip whitespace, punctuation and digits
    import unicodedata
    filtered = "".join(c for c in text if not unicodedata.category(c).startswith(('P', 'N', 'S', 'Z')))
    if not filtered:
        return False
        
    devanagari_count = 0
    for c in filtered:
        if 0x0900 <= ord(c) <= 0x097F:
            devanagari_count += 1
            
    return devanagari_count == len(filtered)

def map_field_result(field_name, claim, word_index, is_readable, anchors_config, image_meta=None):
    """
    Implements the decision tables of F1 1.4/1.6.
    Returns: {"gauntlet_status": str, "reason_code": str|None}
    Possible gauntlet_statuses:
    - "VERIFIED"
    - "ABSENT"
    - "UNREADABLE"
    - "NEEDS_REVIEW"
    - "VERIFY_FAILED"
    """
    has_claim = claim is not None and claim.get("raw") is not None
    
    if not has_claim:
        if not is_readable:
            return {"gauntlet_status": "UNREADABLE", "reason_code": "UNREADABLE_IMAGE"}
        
        # R true, field null
        anchor_present = has_field_anchor(field_name, word_index, anchors_config)
        if anchor_present:
            return {"gauntlet_status": "NEEDS_REVIEW", "reason_code": "EXTRACTION_MISS"}
        else:
            return {"gauntlet_status": "ABSENT", "reason_code": "NOT_PRINTED"}
            
    # Run G1-G5
    # G4 runs first to find the box and overwrite claim["box"], making LLM boxes optional
    g4_pass = check_g4(claim, word_index, image_meta)
    g1_pass = check_g1(claim, word_index, image_meta)
    g2_pass = check_g2(claim, word_index, image_meta)
    g3_pass = check_g3(claim, word_index, image_meta)
    g5_pass = check_g5(claim, field_name, word_index, anchors_config, image_meta)
    
    if not (g1_pass and g2_pass and g3_pass and g4_pass and g5_pass):
        # Is it Devanagari only?
        if is_devanagari_only(claim.get("raw")):
            return {"gauntlet_status": "NEEDS_REVIEW", "reason_code": "UNSUPPORTED_LANGUAGE"}
        else:
            return {"gauntlet_status": "VERIFY_FAILED", "reason_code": "VERIFY_FAILED"}
            
    # All G1-G5 pass
    g6_pass = check_g6(claim, word_index, image_meta)
    if not g6_pass:
        return {"gauntlet_status": "NEEDS_REVIEW", "reason_code": "LOW_CONFIDENCE"}
        
    return {"gauntlet_status": "VERIFIED", "reason_code": None}
