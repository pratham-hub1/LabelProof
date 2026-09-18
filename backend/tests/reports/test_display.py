import pytest
from PIL import Image
from src.reports.display import render_display_image

def test_render_display_image():
    # 2000x1000 image
    img = Image.new('RGB', (2000, 1000), color='white')
    config = {"display_max_edge": 1600}
    
    resized = render_display_image(img, config)
    assert resized.size == (1600, 800)
    
    # Already small
    img2 = Image.new('RGB', (800, 600), color='white')
    resized2 = render_display_image(img2, config)
    assert resized2.size == (800, 600)
