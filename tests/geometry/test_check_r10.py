import pytest
import numpy as np
from PIL import Image, ImageDraw
import io
from src.geometry.check_r10 import check_r10

def create_synthetic_image(fg_color, bg_color):
    img = Image.new('RGB', (100, 100), color=bg_color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([25, 25, 75, 75], fill=fg_color)
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def test_check_r10_pass():
    # Black on white (21:1 contrast)
    img_bytes = create_synthetic_image((0, 0, 0), (255, 255, 255))
    box = {"left": 0, "top": 0, "width": 100, "height": 100}
    
    digit_pixels = np.zeros((100, 100), dtype=bool)
    digit_pixels[25:76, 25:76] = True # The rectangle we drew
    
    res = check_r10(img_bytes, digit_pixels, box, "NOT_MOLDED")
    assert res["status"] == "PASS"
    assert res["contrast"] > 3.5

def test_check_r10_fail():
    # Yellow on white
    img_bytes = create_synthetic_image((255, 255, 0), (255, 255, 255))
    box = {"left": 0, "top": 0, "width": 100, "height": 100}
    
    digit_pixels = np.zeros((100, 100), dtype=bool)
    digit_pixels[25:76, 25:76] = True
    
    res = check_r10(img_bytes, digit_pixels, box, "NOT_MOLDED")
    assert res["status"] == "FAIL"
    assert res["contrast"] < 2.5

def test_check_r10_molded():
    img_bytes = create_synthetic_image((100, 100, 100), (102, 102, 102))
    box = {"left": 0, "top": 0, "width": 100, "height": 100}
    digit_pixels = np.zeros((100, 100), dtype=bool)
    digit_pixels[25:76, 25:76] = True
    
    res = check_r10(img_bytes, digit_pixels, box, "MOLDED")
    assert res["status"] == "NA"
