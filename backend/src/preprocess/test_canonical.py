import pytest
import io
from PIL import Image
import fitz
from backend.src.preprocess.canonical import preprocess

def test_preprocess_jpeg():
    # Create a dummy JPEG image
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    raw_bytes = img_bytes.getvalue()
    
    canonical = preprocess(raw_bytes, 'image/jpeg')
    assert isinstance(canonical, Image.Image)
    assert canonical.size == (100, 100)
    assert canonical.mode == 'RGB'

def test_preprocess_png():
    # Create a dummy PNG image with RGBA
    img = Image.new('RGBA', (50, 50), color='blue')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    raw_bytes = img_bytes.getvalue()
    
    canonical = preprocess(raw_bytes, 'image/png')
    assert isinstance(canonical, Image.Image)
    assert canonical.size == (50, 50)
    assert canonical.mode == 'RGB'  # Should be converted to RGB

def test_preprocess_pdf():
    # Create a dummy PDF with PyMuPDF
    doc = fitz.open()
    page = doc.new_page(width=72, height=72) # 1x1 inch
    page.draw_rect(page.rect, color=(1, 0, 0), fill=(1, 0, 0)) # red page
    raw_bytes = doc.write()
    
    canonical = preprocess(raw_bytes, 'application/pdf')
    assert isinstance(canonical, Image.Image)
    # At 200 DPI, a 1x1 inch page should be 200x200 pixels (roughly)
    # 72 * (200/72) = 200
    assert canonical.size == (200, 200)
    assert canonical.mode == 'RGB'

def test_unsupported_content_type():
    with pytest.raises(ValueError, match="Unsupported content type: text/plain"):
        preprocess(b"hello world", "text/plain")

def test_empty_pdf():
    # Pass an invalid/empty PDF bytes object to trigger empty behavior or exception
    raw_bytes = b""
    with pytest.raises(Exception):
        preprocess(raw_bytes, 'application/pdf')
