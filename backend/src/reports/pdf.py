import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

def generate_pdf(scan_id, record):
    """
    Generates a deterministic PDF report.
    record: The scan record dict.
    Returns: PDF bytes.
    """
    buffer = io.BytesIO()
    
    # invariant=1 makes ReportLab deterministic (fixed CreationDate, no random trailer IDs)
    c = canvas.Canvas(buffer, pagesize=A4, invariant=1)
    
    # Extract data for the report
    verdict = record.get("verdict", "UNKNOWN")
    submitted_at = record.get("submitted_at", "UNKNOWN_TIME")
    
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, f"LabelCheck Report - {scan_id}")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, 770, f"Submitted: {submitted_at}")
    c.drawString(50, 750, f"Verdict: {verdict}")
    
    y = 710
    c.drawString(50, 730, "Field Statuses:")
    field_statuses = record.get("field_status", {})
    for field, status in field_statuses.items():
        c.drawString(70, y, f"{field}: {status}")
        y -= 20
        
    y -= 20
    c.drawString(50, y, "Check Results:")
    y -= 20
    check_results = record.get("check_results", {})
    for check, res in check_results.items():
        c.drawString(70, y, f"{check}: {res.get('status')} - {res.get('fix', '')}")
        y -= 20
        
    # We could add more details, but the spec says "report bytes ... deterministic mode".
    # This minimal content meets the requirement.
    
    c.save()
    return buffer.getvalue()
