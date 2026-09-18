import json
import os

def load_readability_config(config_path=None):
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "readability.config")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_readability(word_index, config=None):
    """
    Computes readability score: R = (OCR word count >= 15) AND (mean OCR word confidence >= 0.65).
    """
    if config is None:
        config = load_readability_config()
        
    min_word_count = config.get("min_word_count", 15)
    min_mean_confidence = config.get("min_mean_confidence", 0.65)
    
    if not word_index:
        return False
        
    word_count = len(word_index)
    if word_count < min_word_count:
        return False
        
    # PDF text layer sets confidence to 1.0, so this handles both
    # Tesseract returns values 0-1, so we average them
    valid_confidences = [w.get("confidence", 0.0) for w in word_index if w.get("confidence") is not None and w.get("confidence") >= 0]
    
    if not valid_confidences:
        return False
        
    mean_confidence = sum(valid_confidences) / len(valid_confidences)
    
    return mean_confidence >= min_mean_confidence
