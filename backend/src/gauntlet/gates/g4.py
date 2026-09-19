import unicodedata
import re

def normalize_text(text):
    """
    N(s) = casefold -> Unicode NFKC -> strip punctuation/symbols -> collapse whitespace.
    Numerals must match exactly in sequence.
    """
    if not text:
        return ""
    # casefold
    text = text.casefold()
    # Unicode NFKC
    text = unicodedata.normalize('NFKC', text)
    # strip punctuation/symbols - keep only alphanumeric and whitespace
    text = re.sub(r'[^\w\s]', '', text)
    # collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def check_g4(claim, word_index, image_meta=None):
    """
    G4: Crop-verify (New Semantics)
    The claimed raw text must match a CONSECUTIVE sequence of words in the Tesseract word_index.
    The field's evidence box becomes the union of the matched OCR word boxes.
    LLM boxes become optional/ignored and are overwritten if a match is found.
    """
    if not claim or "raw" not in claim:
        return False
        
    raw = claim["raw"]
    if raw is None:
        return False
        
    if not word_index:
        return False
        
    norm_raw = normalize_text(raw)
    raw_words = norm_raw.split()
    if not raw_words:
        return False
        
    # Build list of normalized OCR words and their corresponding original word_index entries
    ocr_tokens = []
    for w in word_index:
        nw = normalize_text(w.get("word", ""))
        if nw:
            for sub_w in nw.split():
                ocr_tokens.append((sub_w, w))
                
    n_raw = len(raw_words)
    n_ocr = len(ocr_tokens)
    
    # Find exact sequence match (first in reading order)
    match_start = -1
    for i in range(n_ocr - n_raw + 1):
        match = True
        for j in range(n_raw):
            if ocr_tokens[i+j][0] != raw_words[j]:
                match = False
                break
        if match:
            match_start = i
            break
            
    if match_start == -1:
        return False
        
    # Union the boxes of the matched words
    matched_words = ocr_tokens[match_start : match_start + n_raw]
    
    min_left = float('inf')
    min_top = float('inf')
    max_right = float('-inf')
    max_bottom = float('-inf')
    
    for _, w in matched_words:
        wb = w["box"]
        if isinstance(wb, dict):
            l = wb.get("left", 0)
            t = wb.get("top", 0)
            r = l + wb.get("width", 0)
            b = t + wb.get("height", 0)
        else:
            l, t, r, b = wb
            
        min_left = min(min_left, l)
        min_top = min(min_top, t)
        max_right = max(max_right, r)
        max_bottom = max(max_bottom, b)
        
    if min_left == float('inf'):
        return False
        
    # Overwrite the claim's box with the union box
    claim["box"] = [int(min_left), int(min_top), int(max_right), int(max_bottom)]
    return True
