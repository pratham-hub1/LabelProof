import pytest
import numpy as np
from PIL import Image, ImageDraw

from src.geometry.calibrate import calibrate_photo
from src.geometry.check_r8 import check_r8
from src.geometry.check_r10 import check_r10
from src.geometry.measure import measure_numeral_height

# We will create synthetic images to test F2.

def create_synthetic_rect(width, height, dpi=25.4*25):
    # 25 px/mm
    img = Image.new("RGB", (3000, 3000), (50, 50, 50))
    draw = ImageDraw.Draw(img)
    # Draw a rectangle in the center
    # 50 < A < 100 class
    # width=100, height=80 => area 8000 mm^2 = 80 cm^2 (falls in 50-100 class)
    w_px = int(width * 25)
    h_px = int(height * 25)
    
    left = 1500 - w_px//2
    top = 1500 - h_px//2
    draw.rectangle([left, top, left + w_px, top + h_px], outline="black", width=5, fill=(255, 255, 255))
    
    return img

def create_synthetic_digit(img, digit_height_mm, color=(0,0,0)):
    draw = ImageDraw.Draw(img)
    # 25 px/mm
    h_px = int(digit_height_mm * 25)
    # Draw a "digit" as a solid block inside the rectangle
    left = 1500
    top = 1500
    w_px = h_px // 2
    draw.rectangle([left, top, left + w_px, top + h_px], fill=color)
    # Return a bounding box slightly larger so measure gets background
    return img, [left - 5, top - 5, left + w_px + 5, top + h_px + 5]

from src.geometry.thresholds_loader import load_thresholds_config

def test_f2_1_0mm_fail():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 1.0)
    
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    calib = calibrate_photo(img_bytes, 100.0)
    scale = calib["scale"]
    sigma = calib["sigma"]
    area = calib["pdp_area_cm2"]
    
    h_px = measure_numeral_height(img_bytes, box)
    h_mm = h_px / scale
    
    config = load_thresholds_config()
    res = check_r8(h_mm, area, False, sigma, config)
    assert res["status"] == "FAIL"

def test_f2_2_0mm_pass():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 2.0)
    
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    calib = calibrate_photo(img_bytes, 100.0)
    scale = calib["scale"]
    sigma = calib["sigma"]
    area = calib["pdp_area_cm2"]
    
    h_px = measure_numeral_height(img_bytes, box)
    h_mm = h_px / scale
    
    config = load_thresholds_config()
    res = check_r8(h_mm, area, False, sigma, config)
    assert res["status"] == "PASS"

def test_f2_no_scale():
    img = create_synthetic_rect(100, 80)
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    calib = calibrate_photo(img_bytes, None)
    assert "error" in calib
    assert calib["error"] == "NO_SCALE_REFERENCE"

def test_f2_shadow():
    img = create_synthetic_rect(100, 80)
    # Draw a big shadow that ruins rectangularity
    draw = ImageDraw.Draw(img)
    draw.polygon([(500, 500), (2500, 2500), (1000, 3000)], fill=(128,128,128))
    
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    calib = calibrate_photo(img_bytes, 100.0)
    # The image is ruined, should fail rectangularity or Otsu
    assert "error" in calib

def test_f2_width_off_by_2x():
    img = create_synthetic_rect(100, 80)
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    # Provide 200mm instead of 100mm
    calib = calibrate_photo(img_bytes, 200.0)
    assert "error" in calib
    assert calib["error"] in ["SANITY_CHECK_FAILED", "LOW_RESOLUTION"]

def test_f2_contrast_colors():
    # Yellow on white
    img_y = create_synthetic_rect(100, 80)
    img_y, box_y = create_synthetic_digit(img_y, 2.0, color=(255, 255, 0))
    import io
    buf = io.BytesIO()
    img_y.save(buf, format="JPEG")
    w = box_y[2] - box_y[0]
    h = box_y[3] - box_y[1]
    dp = np.zeros((h, w), dtype=bool)
    dp[5:-5, 5:-5] = True # mock digit mask
    res_y = check_r10(buf.getvalue(), dp, box_y, is_molded=False)
    assert res_y["status"] == "FAIL"
    
    # Grey 160 on white
    img_g = create_synthetic_rect(100, 80)
    img_g, box_g = create_synthetic_digit(img_g, 2.0, color=(160, 160, 160))
    buf = io.BytesIO()
    img_g.save(buf, format="JPEG")
    dp = np.zeros((box_g[3] - box_g[1], box_g[2] - box_g[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    res_g = check_r10(buf.getvalue(), dp, box_g, is_molded=False)
    assert res_g["status"] == "NEEDS_REVIEW"
    
    # Black on white
    img_b = create_synthetic_rect(100, 80)
    img_b, box_b = create_synthetic_digit(img_b, 2.0, color=(0, 0, 0))
    buf = io.BytesIO()
    img_b.save(buf, format="JPEG")
    dp = np.zeros((box_b[3] - box_b[1], box_b[2] - box_b[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    res_b = check_r10(buf.getvalue(), dp, box_b, is_molded=False)
    assert res_b["status"] == "PASS"

def test_f2_determinism():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 2.0)
    
    import io
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    calib1 = calibrate_photo(img_bytes, 100.0)
    calib2 = calibrate_photo(img_bytes, 100.0)
    
    assert calib1 == calib2
    
    h1 = measure_numeral_height(img_bytes, box)
    h2 = measure_numeral_height(img_bytes, box)
    
    assert h1 == h2
    
    dp = np.zeros((box[3] - box[1], box[2] - box[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    r1 = check_r10(img_bytes, dp, box, is_molded=False)
    r2 = check_r10(img_bytes, dp, box, is_molded=False)
    
    assert r1 == r2
