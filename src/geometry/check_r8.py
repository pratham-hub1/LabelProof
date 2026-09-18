import numpy as np
from PIL import Image

def get_required_mm_candidates(pdp_area_cm2, is_molded, rule7_table):
    """
    Returns (R_min, R_max) based on class intervals and area uncertainty.
    """
    sigma_A = pdp_area_cm2 * 0.07 # 7%
    area_min = pdp_area_cm2 - 3 * sigma_A
    area_max = pdp_area_cm2 + 3 * sigma_A
    
    candidates = []
    
    prev_max = 0
    for row in rule7_table:
        # Class interval is (prev_max, max_area]
        # Wait, the spec says "A < 50", "50 < A < 100", etc.
        # But we use intervals [prev_max, max_area)
        class_min = prev_max
        class_max = row["max_area"]
        
        # Check overlap
        # Overlap if max(area_min, class_min) < min(area_max, class_max)
        if max(area_min, class_min) < min(area_max, class_max):
            r = row["molded"] if is_molded else row["normal"]
            candidates.append(r)
            
        prev_max = class_max
        
    if not candidates:
        # Fallback to the largest class if somehow out of bounds
        r = rule7_table[-1]["molded"] if is_molded else rule7_table[-1]["normal"]
        candidates = [r]
        
    return min(candidates), max(candidates)

def check_r8(height_mm, pdp_area_cm2, is_molded, sigma_scale, config):
    """
    Evaluates R8 (numeral height) using the 3-sigma band.
    """
    r_min, r_max = get_required_mm_candidates(pdp_area_cm2, is_molded, config["rule7_table"])
    
    sigma_H = height_mm * sigma_scale
    
    if height_mm + 3 * sigma_H < r_min:
        return {"status": "FAIL", "measured_mm": height_mm, "required_mm": r_min}
    elif height_mm - 3 * sigma_H >= r_max:
        return {"status": "PASS", "measured_mm": height_mm, "required_mm": r_max}
    else:
        return {"status": "NEEDS_REVIEW", "measured_mm": height_mm, "required_mm": f"{r_min}-{r_max}" if r_min != r_max else r_min}

def rgb_to_lab(rgb):
    # Very simple sRGB to Lab (simplified for testing, ideally use skimage.color.rgb2lab if we had it)
    # But wait, we can't use skimage. We must use numpy.
    # We will implement a basic conversion.
    rgb = np.array(rgb, dtype=float) / 255.0
    # sRGB to linear
    mask = rgb > 0.04045
    rgb[mask] = ((rgb[mask] + 0.055) / 1.055) ** 2.4
    rgb[~mask] = rgb[~mask] / 12.92
    
    # linear RGB to XYZ
    matrix = np.array([[0.4124564, 0.3575761, 0.1804375],
                       [0.2126729, 0.7151522, 0.0721750],
                       [0.0193339, 0.1191920, 0.9503041]])
    xyz = np.dot(rgb, matrix.T)
    
    # XYZ to Lab
    xyz_ref_white = np.array([0.95047, 1.00000, 1.08883])
    xyz = xyz / xyz_ref_white
    
    mask = xyz > 0.008856
    xyz[mask] = xyz[mask] ** (1/3)
    xyz[~mask] = (7.787 * xyz[~mask]) + (16 / 116)
    
    L = (116 * xyz[..., 1]) - 16
    a = 500 * (xyz[..., 0] - xyz[..., 1])
    b = 200 * (xyz[..., 1] - xyz[..., 2])
    
    return np.stack([L, a, b], axis=-1)

def calc_contrast(rgb1, rgb2):
    # sRGB to linear for luminance
    def lum(rgb):
        r, g, b = rgb
        r = (r/255.0)
        g = (g/255.0)
        b = (b/255.0)
        r = ((r+0.055)/1.055)**2.4 if r > 0.04045 else r/12.92
        g = ((g+0.055)/1.055)**2.4 if g > 0.04045 else g/12.92
        b = ((b+0.055)/1.055)**2.4 if b > 0.04045 else b/12.92
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
    l1 = lum(rgb1)
    l2 = lum(rgb2)
    l_light = max(l1, l2)
    l_dark = min(l1, l2)
    return (l_light + 0.05) / (l_dark + 0.05)

def detect_embossed(fg_rgb, bg_rgb, config):
    lab1 = rgb_to_lab(fg_rgb)
    lab2 = rgb_to_lab(bg_rgb)
    
    delta_e = np.linalg.norm(lab1 - lab2)
    c = calc_contrast(fg_rgb, bg_rgb)
    
    if delta_e < config["embossed"]["delta_e_max"] and c < config["embossed"]["contrast_max"]:
        return "MOLDED"
    elif delta_e >= config["embossed"]["pale_print_delta_e_min"] and c < config["embossed"]["contrast_max"]:
        return "PALE_PRINT"
    else:
        return "NEEDS_REVIEW"
