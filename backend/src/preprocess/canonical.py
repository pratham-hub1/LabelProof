import io
from PIL import Image, ImageOps
import fitz  # PyMuPDF

def preprocess(raw_bytes: bytes, content_type: str) -> Image.Image:
    """
    Converts raw upload bytes into a canonical PIL Image.
    - Photos (image/jpeg, image/png): applies EXIF transpose to fix rotation, keeps original resolution.
    - PDFs (application/pdf): extracts page 1 at 200 DPI.
    """
    if content_type == 'application/pdf':
        return _preprocess_pdf(raw_bytes)
    elif content_type in ('image/jpeg', 'image/png'):
        return _preprocess_image(raw_bytes)
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

def _preprocess_image(raw_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(raw_bytes))
    # Apply EXIF rotation if present
    canonical = ImageOps.exif_transpose(image)
    # Ensure RGB
    if canonical.mode != 'RGB':
        canonical = canonical.convert('RGB')
    return canonical

def _preprocess_pdf(raw_bytes: bytes) -> Image.Image:
    # PyMuPDF fitz.Document
    doc = fitz.open("pdf", raw_bytes)
    if len(doc) == 0:
        raise ValueError("PDF is empty")
    
    page = doc.load_page(0)  # First page only
    # 200 DPI. PyMuPDF default is 72 DPI. scale = 200 / 72 = 2.777...
    zoom = 200 / 72
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    
    # Convert pixmap to PIL Image
    mode = "RGBA" if pix.alpha else "RGB"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    return img
