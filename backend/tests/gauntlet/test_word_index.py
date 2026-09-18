import io
import pytest
from PIL import Image, ImageDraw
from reportlab.pdfgen import canvas
from src.gauntlet.word_index import build_word_index

def create_test_image():
    # Create a simple image with some text
    img = Image.new('RGB', (200, 100), color=(255, 255, 255))
    # Note: Tesseract might struggle with blank images or simple shapes if they don't look like text,
    # but since this is just a unit test we will mock pytesseract.image_to_data or use a real image.
    # To keep tests fast and deterministic without needing real OCR execution, we'll mock it.
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()

def create_test_pdf():
    pdf_bytes = io.BytesIO()
    c = canvas.Canvas(pdf_bytes, pagesize=(200, 100))
    c.drawString(10, 80, "Hello PDF") # PDF coordinate system has origin at bottom left by default, but reportlab varies.
    c.save()
    return pdf_bytes.getvalue()

def test_build_word_index_image(mocker):
    img_bytes = create_test_image()
    
    # Mock pytesseract
    mock_data = {
        "text": ["", "Hello", "World"],
        "left": [0, 10, 50],
        "top": [0, 20, 20],
        "width": [0, 30, 40],
        "height": [0, 15, 15],
        "conf": ["-1", "95", "88"]
    }
    mocker.patch('pytesseract.image_to_data', return_value=mock_data)
    
    words = build_word_index(img_bytes, content_type="image/jpeg")
    
    assert len(words) == 2
    assert words[0]["word"] == "Hello"
    assert words[0]["confidence"] == 0.95
    assert words[0]["box"]["left"] == 10
    
    assert words[1]["word"] == "World"
    assert words[1]["confidence"] == 0.88

def test_build_word_index_pdf():
    pdf_bytes = create_test_pdf()
    words = build_word_index(pdf_bytes, content_type="application/pdf")
    
    # pdfplumber should extract the text
    assert len(words) > 0
    words_text = [w["word"] for w in words]
    assert "Hello" in words_text
    assert "PDF" in words_text
    
    # Check scaling (200 / 72 = 2.777...)
    # We won't assert exact coordinates because font rendering can vary, but confidence should be 1.0
    assert words[0]["confidence"] == 1.0
