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

def get_words_in_box(word_index, box):
    """
    Get all words from word_index whose center is inside the box.
    Sort by top-to-bottom, left-to-right (roughly).
    """
    if not word_index or not box:
        return ""
        
    if isinstance(box, dict):
        left, top = box.get("left", 0), box.get("top", 0)
        right, bottom = left + box.get("width", 0), top + box.get("height", 0)
    else:
        left, top, right, bottom = box
    
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
            
    # Sort roughly by Y then X
    # Assume lines are roughly 10-20 pixels high, so grouping by Y//15 can help
    # To be robust, sort by Y coordinate
    def get_top_left(x):
        b = x["box"]
        if isinstance(b, dict):
            return b.get("top", 0), b.get("left", 0)
        return b[1], b[0]
    inside_words.sort(key=get_top_left)
    return " ".join(w["word"] for w in inside_words)

def check_g4(claim, word_index, image_meta=None):
    """
    G4: Crop-verify
    normalized OCR text inside the claimed box must match the claimed raw (edit distance = 0)
    """
    if not claim or "raw" not in claim or "box" not in claim:
        return False
        
    raw = claim["raw"]
    if raw is None:
        return False
        
    box = claim["box"]
    if box is None:
        return False
        
    ocr_text = get_words_in_box(word_index, box)
    
    norm_raw = normalize_text(raw)
    norm_ocr = normalize_text(ocr_text)
    
    # To avoid substring matches of numerals (e.g., "12" inside "120"),
    # we match the exact sequence of normalized words.
    raw_words = norm_raw.split()
    ocr_words = norm_ocr.split()
    
    if not raw_words:
        return False
        
    n_raw = len(raw_words)
    n_ocr = len(ocr_words)
    for i in range(n_ocr - n_raw + 1):
        if ocr_words[i:i+n_raw] == raw_words:
            return True
            
    return False
