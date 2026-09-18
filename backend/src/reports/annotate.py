from PIL import Image, ImageDraw, ImageFont
import json

def get_color(status: str, config: dict) -> str:
    # Colors: FAIL red, PASS green, NEEDS_REVIEW amber (NA-with-box also amber)
    if status == 'NA':
        return config['colors'].get('NEEDS_REVIEW', '#FFA500')
    return config['colors'].get(status, '#FFA500')

def render_annotated(canonical_image: Image.Image, results: dict, exemption: dict, summary: dict, config: dict) -> Image.Image:
    """
    Renders the annotated image.
    Validates boxes, groups identical boxes, draws rectangles and stacked labels, and prepends a legend banner.
    """
    img = canonical_image.copy()
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    width, height = img.size
    draw = ImageDraw.Draw(img)
    stroke_width = max(3, width // 400)
    
    # 1. Group boxes
    # boxes_map keyed by tuple(ymin, xmin, ymax, xmax) -> list of (rule_id, status)
    boxes_map = {}
    
    for rule_id, res in results.items():
        box = res.get('box')
        if not box:
            continue
            
        # Extract and validate box
        # Format: {"ymin": 0.1, "xmin": 0.1, "ymax": 0.2, "xmax": 0.2}
        try:
            ymin, xmin = box['ymin'], box['xmin']
            ymax, xmax = box['ymax'], box['xmax']
        except KeyError:
            continue
            
        # In-bounds validation: 0.0 to 1.0
        if not (0.0 <= ymin <= 1.0 and 0.0 <= xmin <= 1.0 and 0.0 <= ymax <= 1.0 and 0.0 <= xmax <= 1.0):
            continue
        if ymin >= ymax or xmin >= xmax:
            continue
            
        # Use rounded coordinates for grouping to avoid floating point issues
        coord_key = (round(ymin, 4), round(xmin, 4), round(ymax, 4), round(xmax, 4))
        if coord_key not in boxes_map:
            boxes_map[coord_key] = []
            
        boxes_map[coord_key].append((rule_id, res.get('status', 'NA')))
        
    # Default font
    try:
        font = ImageFont.truetype("arial.ttf", max(12, width // 60))
    except IOError:
        font = ImageFont.load_default()
        
    # 2. Draw boxes and chips
    for (ymin, xmin, ymax, xmax), labels in boxes_map.items():
        left = xmin * width
        top = ymin * height
        right = xmax * width
        bottom = ymax * height
        
        # Determine main color (if any FAIL, red; else if NEEDS_REVIEW/NA, amber; else green)
        statuses = [s for r, s in labels]
        if 'FAIL' in statuses:
            color = get_color('FAIL', config)
        elif 'NEEDS_REVIEW' in statuses or 'NA' in statuses:
            color = get_color('NEEDS_REVIEW', config)
        else:
            color = get_color('PASS', config)
            
        draw.rectangle([left, top, right, bottom], outline=color, width=stroke_width)
        
        # Draw stacked labels
        chip_y = top
        for rule_id, status in labels:
            text = f"{rule_id} {status}"
            # getbbox returns (left, top, right, bottom)
            bbox = font.getbbox(text) if hasattr(font, 'getbbox') else draw.textbbox((0,0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Draw background for text
            chip_top = chip_y - text_height - 4 - stroke_width
            if chip_top < 0:
                chip_top = chip_y + stroke_width # Push below if off-screen
                
            draw.rectangle(
                [left, chip_top, left + text_width + 4, chip_top + text_height + 4],
                fill=color
            )
            draw.text((left + 2, chip_top + 2), text, fill="black", font=font)
            
            chip_y = chip_top
            
    # 3. Prepend banner
    is_exempt = exemption.get('applied', False)
    if is_exempt:
        banner_text = f"EXEMPT — {exemption.get('rule', 'Rule 26(a)')}"
        banner_color = config['colors'].get('EXEMPT', '#808080')
    else:
        banner_text = f"{summary.get('pass', 0)} PASS \u00B7 {summary.get('fail', 0)} FAIL \u00B7 {summary.get('na', 0)} NA \u00B7 {summary.get('needs_review', 0)} NEEDS_REVIEW"
        if summary.get('fail', 0) > 0:
            banner_color = config['colors'].get('FAIL', '#FF0000')
        elif summary.get('needs_review', 0) > 0:
            banner_color = config['colors'].get('NEEDS_REVIEW', '#FFA500')
        else:
            banner_color = config['colors'].get('PASS', '#00FF00')
            
    banner_height = max(40, height // 20)
    try:
        banner_font = ImageFont.truetype("arial.ttf", banner_height // 2)
    except IOError:
        banner_font = ImageFont.load_default()
        
    final_img = Image.new('RGB', (width, height + banner_height), color=banner_color)
    final_img.paste(img, (0, banner_height))
    
    banner_draw = ImageDraw.Draw(final_img)
    
    bbox = banner_font.getbbox(banner_text) if hasattr(banner_font, 'getbbox') else banner_draw.textbbox((0,0), banner_text, font=banner_font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    banner_draw.text(((width - text_w) // 2, (banner_height - text_h) // 2), banner_text, fill="white", font=banner_font)
    
    return final_img
