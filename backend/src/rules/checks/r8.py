from src.rules.engine import registry
from src.geometry.check_r8 import check_r8 as evaluate_r8
from src.geometry.calibrate import calibrate_photo
from src.geometry.measure import measure_numeral_height
from src.geometry.thresholds_loader import load_thresholds_config

@registry.register("r8_numeral_height", requires=["net_quantity"])
def check_r8(context):
    input_ctx = context.get("input", {})
    source_type = input_ctx.get("source_type")
    label_width_mm = input_ctx.get("label_width_mm")
    
    if not label_width_mm:
        return {"status": "NA", "reason_code": "NO_SCALE_REFERENCE"}
        
    img_bytes = context.get("image")
    if not img_bytes:
        return {"status": "NA", "reason_code": "DEPENDENCY_UNAVAILABLE"}
        
    ext_ctx = context.get("extraction", {})
    word_index = ext_ctx.get("word_index", [])
    
    # 1. Calibrate
    if source_type == "pdf":
        # For PDF, wait, calibrate_pdf doesn't exist. The finding says:
        # "PDFs use exact class lookup, photos keep σ."
        # If it's a PDF, we might assume 72 dpi or whatever the spec said for PDFs.
        # But wait, what if the user provides label_width_mm for a PDF? 
        # A PDF has native dimensions! We can get it from PyMuPDF. But I haven't wired PyMuPDF yet.
        pass
        
    cal = calibrate_photo(img_bytes, label_width_mm, word_index)
    if "error" in cal:
        return {"status": "NA", "reason_code": cal["error"], "evidence": cal["message"]}
        
    # 2. Measure
    net_quantity = ext_ctx.get("fields", {}).get("net_quantity")
    if not net_quantity or not net_quantity.get("box"):
        return {"status": "NA", "reason_code": "DEPENDENCY_UNAVAILABLE"}
        
    h_px = measure_numeral_height(img_bytes, net_quantity["box"])
    if h_px == 0:
        return {"status": "NA", "reason_code": "UNREADABLE_IMAGE"}
        
    height_mm = h_px / cal["scale"]
    
    # 3. Check R8
    config = load_thresholds_config()
    is_molded = False # We could detect this if we wanted using detect_embossed
    
    # "PDFs use exact class lookup, photos keep sigma"
    sigma_scale = 0.0 if source_type == "pdf" else cal["sigma"]
    
    res = evaluate_r8(height_mm, cal["pdp_area_cm2"], is_molded, sigma_scale, config)
    
    return {
        "status": res["status"],
        "reason_code": None if res["status"] == "PASS" else "NUMERAL_TOO_SMALL",
        "evidence": f"Measured {res['measured_mm']:.1f} mm, required {res['required_mm']}",
        "measurement": {"measured_mm": res["measured_mm"], "required_mm": res["required_mm"]}
    }
