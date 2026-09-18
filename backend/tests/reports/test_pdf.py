import pytest
import io
from PIL import Image
from src.reports.pdf import build_pdf_report, sanitize_pdf_text

def test_sanitize_pdf_text():
    assert sanitize_pdf_text("Hello World") == "Hello World"
    # non-Latin
    devanagari = "नमस्ते"
    assert sanitize_pdf_text(devanagari) == "[non-Latin text — see JSON report]"

def test_build_pdf_report():
    # Make a dummy image
    img = Image.new('RGB', (100, 100), color='white')
    img_io = io.BytesIO()
    img.save(img_io, format='JPEG')
    img_bytes = img_io.getvalue()
    
    scan_fields = {
        "created_at": "2026-09-18T10:00:00Z",
        "input": {"source_type": "pdf", "page_count": 2}
    }
    results = {
        "R1": {"name": "Test Rule", "status": "FAIL", "evidence": "something", "fix": "fix it", "anchored": False},
        "R2": {"name": "Verified Rule", "status": "VERIFIED", "evidence": {"key": "val"}, "anchored": False}
    }
    exemption = {"applied": True, "rule": "Rule 26(a)"}
    found_declarations = 5
    config = {'margins': {'left': 36, 'right': 36, 'top': 36, 'bottom': 36}}
    
    pdf_bytes1 = build_pdf_report(scan_fields, results, exemption, found_declarations, config, img_bytes)
    assert pdf_bytes1.startswith(b'%PDF')
    
    pdf_bytes2 = build_pdf_report(scan_fields, results, exemption, found_declarations, config, img_bytes)
    assert pdf_bytes1 == pdf_bytes2 # Determinism
