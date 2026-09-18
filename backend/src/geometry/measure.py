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
        
    from src.geometry.calibrate import min_area_rect
    objects = find_objects(labeled_array)
    
    heights = []
    for i, obj in enumerate(objects, start=1):
        if obj is None:
            continue
            
        h_bb = obj[0].stop - obj[0].start
        w_bb = obj[1].stop - obj[1].start
        
        # Basic noise filtering
        if h_bb > 2 and w_bb > 1:
            # Use PCA minAreaRect for rotation-invariant dimensions
            y, x = np.nonzero(labeled_array[obj] == i)
            # Offset by object start to get global coordinates if needed, 
            # but min_area_rect centers them anyway, so local coordinates are fine!
            points = np.column_stack((y, x))
            w, h = min_area_rect(points)
            
            # min_area_rect returns (max_extent, min_extent). For numerals, height is the max extent.
            heights.append(max(w, h))
            
    if not heights:
        return 0.0
        
    return float(np.median(heights))
