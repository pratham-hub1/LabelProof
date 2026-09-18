from PIL import Image, ImageDraw
import io
from src.geometry.calibrate import calibrate_photo
from src.geometry.measure import measure_numeral_height
from src.geometry.check_r8 import check_r8
from src.geometry.thresholds_loader import load_thresholds_config

def create_synthetic_rect(width, height, dpi=25.4*25):
    img = Image.new("RGB", (3000, 3000), (50, 50, 50))
    draw = ImageDraw.Draw(img)
    w_px = int(width * 25)
    h_px = int(height * 25)
    left = 1500 - w_px//2
    top = 1500 - h_px//2
    draw.rectangle([left, top, left + w_px, top + h_px], outline="black", width=5, fill=(255, 255, 255))
    return img

def create_synthetic_digit(img, digit_height_mm, color=(0,0,0)):
    draw = ImageDraw.Draw(img)
    h_px = int(digit_height_mm * 25)
    left = 1500
    top = 1500
    w_px = h_px // 2
    draw.rectangle([left, top, left + w_px, top + h_px], fill=color)
    return img, [left - 10, top - 10, left + w_px + 10, top + h_px + 10]

img = create_synthetic_rect(100, 80)
img, box = create_synthetic_digit(img, 1.46)
buf = io.BytesIO()
img.save(buf, format="JPEG")
img_bytes = buf.getvalue()
calib = calibrate_photo(img_bytes, 100.0)
h_px = measure_numeral_height(img_bytes, box)
h_mm = h_px / calib["scale"]
print(f"h_mm measured: {h_mm}")
config = load_thresholds_config()
res = check_r8(h_mm, calib["pdp_area_cm2"], False, calib["sigma"], config)
print(res)
