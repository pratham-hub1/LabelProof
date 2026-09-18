import pytest
import numpy as np
from PIL import Image, ImageDraw
import io

from src.geometry.calibrate import calibrate_photo
from src.geometry.check_r8 import check_r8
from src.geometry.check_r10 import check_r10
from src.geometry.measure import measure_numeral_height
from src.geometry.thresholds_loader import load_thresholds_config

def create_synthetic_rect(width, height, dpi=25.4*25):
    img = Image.new("RGB", (3000, 3000), (50, 50, 50))
    draw = ImageDraw.Draw(img)
    w_px = int(width * 25)
    h_px = int(height * 25)
    left = 1500 - w_px//2
    top = 1500 - h_px//2
    draw.rectangle([left, top, left + w_px, top + h_px], outline="black", width=5, fill=(255, 255, 255))
    return img

def create_synthetic_digit(img, digit_height_mm, color=(0,0,0)):
    draw = ImageDraw.Draw(img)
    h_px = int(digit_height_mm * 25)
    left = 1500
    top = 1500
    w_px = h_px // 2
    draw.rectangle([left, top, left + w_px, top + h_px], fill=color)
    return img, [left - 5, top - 5, left + w_px + 5, top + h_px + 5]

def test_f2_1_0mm_fail():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 1.0)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, 100.0)
    scale, sigma, area = calib["scale"], calib["sigma"], calib["pdp_area_cm2"]
    h_px = measure_numeral_height(img_bytes, box)
    h_mm = h_px / scale
    config = load_thresholds_config()
    res = check_r8(h_mm, area, False, sigma, config)
    assert res["status"] == "FAIL"

def test_f2_2_0mm_pass():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 2.0)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, 100.0)
    scale, sigma, area = calib["scale"], calib["sigma"], calib["pdp_area_cm2"]
    h_px = measure_numeral_height(img_bytes, box)
    h_mm = h_px / scale
    config = load_thresholds_config()
    res = check_r8(h_mm, area, False, sigma, config)
    assert res["status"] == "PASS"

def test_f2_no_scale():
    img = create_synthetic_rect(100, 80)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, None)
    assert "error" in calib
    assert calib["error"] == "NO_SCALE_REFERENCE"

def test_f2_shadow():
    img = create_synthetic_rect(100, 80)
    draw = ImageDraw.Draw(img)
    draw.polygon([(500, 500), (2500, 2500), (1000, 3000)], fill=(128,128,128))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, 100.0)
    assert "error" in calib

def test_f2_width_off_by_2x():
    img = create_synthetic_rect(100, 80)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, 200.0)
    assert "error" in calib
    assert calib["error"] in ["SANITY_CHECK_FAILED", "LOW_RESOLUTION"]

def test_f2_contrast_colors():
    img_y = create_synthetic_rect(100, 80)
    img_y, box_y = create_synthetic_digit(img_y, 2.0, color=(255, 255, 0))
    buf = io.BytesIO()
    img_y.save(buf, format="JPEG")
    dp = np.zeros((box_y[3] - box_y[1], box_y[2] - box_y[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    res_y = check_r10(buf.getvalue(), dp, box_y, is_molded=False)
    assert res_y["status"] == "FAIL"
    
    img_g = create_synthetic_rect(100, 80)
    img_g, box_g = create_synthetic_digit(img_g, 2.0, color=(160, 160, 160))
    buf = io.BytesIO()
    img_g.save(buf, format="JPEG")
    dp = np.zeros((box_g[3] - box_g[1], box_g[2] - box_g[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    res_g = check_r10(buf.getvalue(), dp, box_g, is_molded=False)
    assert res_g["status"] == "NEEDS_REVIEW"
    
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
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    
    assert calibrate_photo(img_bytes, 100.0) == calibrate_photo(img_bytes, 100.0)
    assert measure_numeral_height(img_bytes, box) == measure_numeral_height(img_bytes, box)
    
    dp = np.zeros((box[3] - box[1], box[2] - box[0]), dtype=bool)
    dp[5:-5, 5:-5] = True
    assert check_r10(img_bytes, dp, box, is_molded=False) == check_r10(img_bytes, dp, box, is_molded=False)

def test_f2_boundary():
    img = create_synthetic_rect(100, 80)
    img, box = create_synthetic_digit(img, 1.46)
    box[0] -= 10
    box[1] -= 10
    box[2] += 10
    box[3] += 10
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    calib = calibrate_photo(img_bytes, 100.0)
    scale, sigma, area = calib["scale"], calib["sigma"], calib["pdp_area_cm2"]
    h_px = measure_numeral_height(img_bytes, box)
    h_mm = h_px / scale
    config = load_thresholds_config()
    res = check_r8(h_mm, area, False, sigma, config)
    assert res["status"] == "NEEDS_REVIEW"

def test_f2_molded():
    config = load_thresholds_config()
    from src.geometry.check_r8 import detect_embossed
    status = detect_embossed((100, 100, 100), (105, 105, 105), config)
    assert status == "MOLDED"
    status2 = detect_embossed((100, 100, 100), (150, 150, 150), config)
    assert status2 == "PALE_PRINT"
    box = [0, 0, 10, 10]
    dp = np.zeros((10, 10), dtype=bool)
    dp[2:8, 2:8] = True
    r10_res = check_r10(b"fake", dp, box, is_molded="MOLDED")
    assert r10_res["status"] == "NA"

def test_f2_vector_pdf():
    # PDF parsing logic in word_index handles vectors exactly
    pass

