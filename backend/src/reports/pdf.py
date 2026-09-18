import io
import json
import re
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

def sanitize_pdf_text(text: str) -> str:
    """
    Replaces non-Latin glyphs with a placeholder, as reportlab standard fonts
    cannot shape complex scripts like Devanagari.
    """
    if not isinstance(text, str):
        return str(text)
    try:
        text.encode('latin-1')
        return text
    except UnicodeEncodeError:
        # F6.4 requires placeholder
        return "[non-Latin text — see JSON report]"

class InvariantDocTemplate(SimpleDocTemplate):
    def handle_pageBegin(self):
        super().handle_pageBegin()
        self.canv.setCreator("LabelProof")
        self.canv.setProducer("LabelProof")
        
    def build(self, flowables, onFirstPage=None, onLaterPages=None, canvasmaker=canvas.Canvas):
        def invariant_canvas(*args, **kwargs):
            kwargs['invariant'] = 1
            kwargs['pageCompression'] = 0
            return canvasmaker(*args, **kwargs)
        super().build(flowables, onFirstPage=onFirstPage, onLaterPages=onLaterPages, canvasmaker=invariant_canvas)

def build_pdf_report(scan_fields: dict, results: dict, exemption: dict, found_declarations: int, config: dict, annotated_image_bytes: bytes) -> bytes:
    """
    Builds the PDF report using reportlab in invariant mode.
    """
    buffer = io.BytesIO()
    
    margins = config.get('margins', {'left': 36, 'right': 36, 'top': 36, 'bottom': 36})
    doc = InvariantDocTemplate(
        buffer, 
        pagesize=letter,
        leftMargin=margins['left'],
        rightMargin=margins['right'],
        topMargin=margins['top'],
        bottomMargin=margins['bottom']
    )
    
    styles = getSampleStyleSheet()
    story = []
    
    # 1. Annotated Image (Page 1)
    if annotated_image_bytes:
        img_io = io.BytesIO(annotated_image_bytes)
        from PIL import Image as PILImage
        with PILImage.open(img_io) as pil_img:
            w, h = pil_img.size
            
        available_width = letter[0] - margins['left'] - margins['right']
        available_height = letter[1] - margins['top'] - margins['bottom'] - 50
        
        scale = min(available_width / w, available_height / h)
        pdf_img = Image(img_io, width=w * scale, height=h * scale)
        story.append(pdf_img)
        
    # Note for multi-page
    is_multi = scan_fields.get('input', {}).get('source_type') == 'pdf' and scan_fields.get('input', {}).get('page_count', 1) > 1
    if is_multi:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Note: Input was a multi-page PDF. Only the first page was processed.", styles['Italic']))
        
    # 2. Exemption Banner
    if exemption.get('applied', False):
        story.append(Spacer(1, 12))
        banner = Paragraph(f"<font color='gray'><b>EXEMPT — {exemption.get('rule', 'Rule 26(a)')}</b></font>", styles['Heading2'])
        story.append(banner)
        
    # 3. Summary Text
    story.append(Spacer(1, 24))
    story.append(Paragraph(f"Found {found_declarations} of 7 declarations", styles['Heading2']))
    story.append(Spacer(1, 12))
    
    # 4. Results Table
    table_data = [["Rule ID", "Name", "Status", "Evidence", "Fix"]]
    
    for rule_id, res in results.items():
        name = res.get('name', '')
        status = res.get('status', 'NA')
        
        # Evidence handling
        evidence = res.get('evidence', '')
        if isinstance(evidence, dict) or isinstance(evidence, list):
            evidence = json.dumps(evidence)
        elif res.get('measurement'):
            evidence = json.dumps(res.get('measurement'))
            
        evidence = sanitize_pdf_text(str(evidence))
        fix = sanitize_pdf_text(res.get('fix', ''))
        
        # Add unanchored-verified tag
        if status == 'VERIFIED' and res.get('anchored') is False:
            status = 'VERIFIED\n(unanchored-verified)'
            
        table_data.append([
            rule_id,
            Paragraph(name, styles['Normal']),
            status,
            Paragraph(evidence, styles['Normal']),
            Paragraph(fix, styles['Normal'])
        ])
        
    t = Table(table_data, colWidths=[1*inch, 1.5*inch, 1*inch, 2*inch, 1.5*inch], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(t)
    
    # Footer
    def add_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 9)
        canvas.drawString(margins['left'], margins['bottom'] - 20, "This tool assumes non-exempt retail packaged goods.")
        # Timestamps from record
        created_at = scan_fields.get('created_at', '')
        canvas.drawRightString(letter[0] - margins['right'], margins['bottom'] - 20, f"Scan Created: {created_at}")
        canvas.restoreState()
        
    doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
    
    return buffer.getvalue()
