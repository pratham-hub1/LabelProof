import pytest
import numpy as np
from PIL import Image, ImageDraw
import io
from src.geometry.calibrate import calibrate_photo

def create_synthetic_image(width, height, rect_w, rect_h, add_shadow=False):
    img = Image.new('L', (width, height), color=255) # white bg
    draw = ImageDraw.Draw(img)
    # Draw a dark gray rectangle in the center
    left = (width - rect_w) // 2
    top = (height - rect_h) // 2
    draw.rectangle([left, top, left + rect_w - 1, top + rect_h - 1], fill=100)
    
    if add_shadow:
        # Draw a big shadow that breaks rectangularity
        draw.polygon([(left, top), (left - 50, top + 50), (left - 50, bottom + 50), (left, bottom)], fill=150)
        
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def test_calibrate_no_scale():
    res = calibrate_photo(b"mock", None)
    assert res["error"] == "NO_SCALE_REFERENCE"

def test_calibrate_success():
    # 100x50 mm label at 25 px/mm -> 2500x1250 px
    img_bytes = create_synthetic_image(3000, 2000, 2500, 1250)
    res = calibrate_photo(img_bytes, 100.0)
    
    assert "error" not in res
    assert np.isclose(res["scale"], 25.0, rtol=0.05) # 25 px/mm
    assert res["sigma"] == 0.05
    # Area = 10cm x 5cm = 50 cm^2
    assert np.isclose(res["pdp_area_cm2"], 50.0, rtol=0.05)

def test_calibrate_low_resolution():
    # 100x50 mm label at 10 px/mm -> 1000x500 px
    img_bytes = create_synthetic_image(1500, 1000, 1000, 500)
    res = calibrate_photo(img_bytes, 100.0)
    assert res["error"] == "LOW_RESOLUTION"

def test_calibrate_shadow_merge():
    # Needs a shadow that breaks rectangularity < 0.8
    # We can just mock a mask or create one
    img = Image.new('L', (1000, 1000), color=255)
    draw = ImageDraw.Draw(img)
    draw.ellipse([200, 200, 800, 800], fill=100) # Circle has rectangularity pi/4 ~ 0.785 < 0.80
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    
    # We need to lower the threshold to let it pass low resolution check
    # Wait, low resolution check runs AFTER rectangularity check.
    res = calibrate_photo(img_bytes.getvalue(), 100.0)
    assert res["error"] == "SHADOW_MERGE"
