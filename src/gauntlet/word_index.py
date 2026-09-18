import io
import pytesseract
import pdfplumber
from PIL import Image

def build_word_index(document_bytes, content_type="image/jpeg"):
    """
    Builds a word index from an image or PDF.
    Returns: list of { "word": str, "box": {"left": int, "top": int, "width": int, "height": int}, "confidence": float }
    """
    words = []
    
    if content_type == "application/pdf":
        # Extract from PDF text layer using pdfplumber
        # Coordinate system must match the canonical image (200 DPI)
        scale = 200 / 72
        
        with pdfplumber.open(io.BytesIO(document_bytes)) as pdf:
            if not pdf.pages:
                return []
            page = pdf.pages[0]
            # pdfplumber extract_words() returns [{'text': text, 'x0': x0, 'top': top, 'x1': x1, 'bottom': bottom}]
            extracted = page.extract_words()
            
            for w in extracted:
                text = w["text"].strip()
                if not text:
                    continue
                left = w["x0"] * scale
                top = w["top"] * scale
                right = w["x1"] * scale
                bottom = w["bottom"] * scale
                
                words.append({
                    "word": text,
                    "box": {
                        "left": round(left),
                        "top": round(top),
                        "width": round(right - left),
                        "height": round(bottom - top)
                    },
                    "confidence": 1.0  # PDF text layer is exact
                })
    else:
        # Extract from image using Tesseract
        image = Image.open(io.BytesIO(document_bytes))
        data = pytesseract.image_to_data(image, lang="eng+hin", output_type=pytesseract.Output.DICT)
        
        for i in range(len(data["text"])):
            text = data["text"][i].strip()
            conf = data["conf"][i]
            
            # Tesseract returns conf as string or int from 0 to 100, or -1 for empty
            try:
                conf = float(conf)
            except ValueError:
                conf = -1.0
                
            if not text or conf < 0:
                continue
                
            words.append({
                "word": text,
                "box": {
                    "left": data["left"][i],
                    "top": data["top"][i],
                    "width": data["width"][i],
                    "height": data["height"][i]
                },
                "confidence": round(conf / 100.0, 2)
            })
            
    return words
