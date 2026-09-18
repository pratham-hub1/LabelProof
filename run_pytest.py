import pytest
from tests.acceptance.test_f2 import *

img = create_synthetic_rect(100, 80)
img, box = create_synthetic_digit(img, 1.46)
buf = io.BytesIO()
img.save(buf, format="JPEG")
img_bytes = buf.getvalue()
calib = calibrate_photo(img_bytes, 100.0)
h_px = measure_numeral_height(img_bytes, box)
h_mm = h_px / calib["scale"]
config = load_thresholds_config()
res = check_r8(h_mm, calib["pdp_area_cm2"], False, calib["sigma"], config)
assert res["status"] == "NEEDS_REVIEW"
