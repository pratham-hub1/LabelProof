import pytest
from src.reports.pdf import generate_pdf

def test_generate_pdf_deterministic():
    scan_id = "test-scan-123"
    record = {
        "submitted_at": "2026-09-18T10:00:00Z",
        "verdict": "FAILED",
        "field_status": {
            "mrp": "VERIFIED"
        },
        "check_results": {
            "r1": {"status": "FAIL", "fix": "Add name"}
        }
    }
    
    pdf1 = generate_pdf(scan_id, record)
    pdf2 = generate_pdf(scan_id, record)
    
    assert pdf1 == pdf2
