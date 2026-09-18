from PIL import Image

def render_display_image(canonical_image: Image.Image, config: dict) -> Image.Image:
    """
    Resizes the image to max edge specified in config (e.g., 1600), only if larger.
    Returns the new PIL Image (or a copy of the original).
    """
    img = canonical_image.copy()
    if img.mode != 'RGB':
        img = img.convert('RGB')
        
    max_edge = config.get('display_max_edge', 1600)
    width, height = img.size
    
    if width > max_edge or height > max_edge:
        if width > height:
            new_width = max_edge
            new_height = int(height * (max_edge / width))
        else:
            new_height = max_edge
            new_width = int(width * (max_edge / height))
            
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
    return img
