import pytest
import numpy as np
from PIL import Image, ImageDraw
import io
from src.geometry.measure import measure_numeral_height

def create_test_image_with_digits():
    img = Image.new('RGB', (100, 100), color='white')
    draw = ImageDraw.Draw(img)
    # Draw a mock digit (rectangle)
    # Height is 20 pixels
    draw.rectangle([10, 10, 20, 30], fill='black')
    
    # Draw another digit, height 22
    draw.rectangle([30, 10, 40, 32], fill='black')
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

def test_measure_numeral_height():
    img_bytes = create_test_image_with_digits()
    box = {"left": 0, "top": 0, "width": 100, "height": 50}
    
    height = measure_numeral_height(img_bytes, box)
    
    # We expect median of 20 and 22, which is 21.0 (or 21/23 -> 22.0 depending on inclusive pixels)
    # Actually PCA extents on pixel centers is 20 and 22, median is 21.0
    assert height == 21.0
    
def test_measure_numeral_height_empty():
    img = Image.new('RGB', (100, 100), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    
    box = {"left": 0, "top": 0, "width": 100, "height": 50}
    height = measure_numeral_height(img_bytes.getvalue(), box)
    assert height == 0.0

def test_measure_numeral_height_invalid_box():
    img_bytes = create_test_image_with_digits()
    box = {"left": 100, "top": 100, "width": 10, "height": 10}
    height = measure_numeral_height(img_bytes, box)
    assert height == 0.0

def test_measure_tight_crop():
    # Bug fix: mask flip on tight crops.
    # If we crop tightly around a digit, the digit (black) might be MORE than 50% of the area!
    # A simple area check would flip it, making white the object, measuring the holes.
    img = Image.new('L', (20, 40), color=255) # white bg
    draw = ImageDraw.Draw(img)
    # Draw a huge thick black box that takes up most of the crop
    draw.rectangle([2, 2, 18, 38], fill=0)
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    
    h = measure_numeral_height(img_bytes.getvalue(), [0, 0, 20, 40])
    
    # 38 - 2 = 36 px height
    assert np.isclose(h, 36.0, atol=2.0)
