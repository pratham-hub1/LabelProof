import numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects
import io

def measure_numeral_height(image, box):
    """
    Measures the median digit height in pixels inside the box.
    image: PIL.Image or bytes
    box: dict with left, top, width, height
    """
    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image))
        
    left, top, right, bottom = box
    
    left, top = max(0, left), max(0, top)
    right, bottom = min(image.width, right), min(image.height, bottom)
    
    if right <= left or bottom <= top:
        return 0.0
        
    crop = image.crop((left, top, right, bottom))
    gray = crop.convert('L')
    arr = np.array(gray)
    
    # Otsu-like behavior or simple mean
    threshold = np.mean(arr)
    binary = arr < threshold
    
    # Assume text is foreground (less area than background)
    if np.sum(binary) > np.sum(~binary):
        binary = ~binary
        
    labeled_array, num_features = label(binary)
    if num_features == 0:
        return 0.0
        
    objects = find_objects(labeled_array)
    
    heights = []
    for obj in objects:
        if obj is None:
            continue
        h = obj[0].stop - obj[0].start
        w = obj[1].stop - obj[1].start
        
        # Basic noise filtering
        if h > 2 and w > 1:
            heights.append(h)
            
    if not heights:
        return 0.0
        
    return float(np.median(heights))
