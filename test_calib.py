from PIL import Image, ImageDraw
import io
from src.geometry.calibrate import calibrate_photo
from src.geometry.measure import measure_numeral_height
def create_synthetic_rect(width, height, dpi=25.4*25):
    img = Image.new("RGB", (3000, 3000), (50, 50, 50))
    draw = ImageDraw.Draw(img)
    w_px = int(width * 25)
    h_px = int(height * 25)
    left = 1500 - w_px//2
    top = 1500 - h_px//2
    draw.rectangle([left, top, left + w_px, top + h_px], outline="black", width=5, fill=(255, 255, 255))
    return img

img = create_synthetic_rect(100, 80)
buf = io.BytesIO()
img.save(buf, format="JPEG")
img_bytes = buf.getvalue()
calib = calibrate_photo(img_bytes, 100.0)
print(calib)
