import numpy as np
from PIL import Image
import io
from src.geometry.check_r8 import calc_contrast
from src.geometry.thresholds_loader import load_thresholds_config

def check_r10(image, digit_pixels, box, is_molded):
    """
    Evaluates R10 (WCAG contrast).
    digit_pixels: binary numpy array matching the box size.
    """
    if is_molded == "MOLDED":
        return {"status": "NA", "reason": "No contrast required on glass/plastic (embossed)"}
        
    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image))
        
    left, top = int(box["left"]), int(box["top"])
    right, bottom = left + int(box["width"]), top + int(box["height"])
    
    crop = image.crop((left, top, right, bottom)).convert('RGB')
    arr = np.array(crop)
    
    # Extract FG and BG colors
    if not np.any(digit_pixels):
        return {"status": "NEEDS_REVIEW", "reason": "No digit pixels found"}
    if not np.any(~digit_pixels):
        return {"status": "NEEDS_REVIEW", "reason": "No background pixels found"}
        
    fg_pixels = arr[digit_pixels]
    bg_pixels = arr[~digit_pixels]
    
    fg_rgb = np.median(fg_pixels, axis=0)
    bg_rgb = np.median(bg_pixels, axis=0)
    
    c = calc_contrast(fg_rgb, bg_rgb)
    
    config = load_thresholds_config()
    pass_min = config["contrast"]["pass_min"]
    fail_max = config["contrast"]["fail_max"]
    
    if c >= pass_min:
        return {"status": "PASS", "contrast": c, "fg": fg_rgb.tolist(), "bg": bg_rgb.tolist()}
    elif c <= fail_max:
        return {"status": "FAIL", "contrast": c, "fg": fg_rgb.tolist(), "bg": bg_rgb.tolist()}
    else:
        return {"status": "NEEDS_REVIEW", "contrast": c, "fg": fg_rgb.tolist(), "bg": bg_rgb.tolist()}
