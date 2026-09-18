from src.geometry.thresholds_loader import load_thresholds_config
from src.geometry.check_r8 import detect_embossed
config = load_thresholds_config()
print("MOLDED:")
print(detect_embossed((100, 100, 100), (105, 105, 105), config))
print("PALE_PRINT 120:")
print(detect_embossed((100, 100, 100), (120, 120, 120), config))
print("PALE_PRINT 150:")
print(detect_embossed((100, 100, 100), (150, 150, 150), config))
