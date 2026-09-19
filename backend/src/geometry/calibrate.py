import numpy as np
from PIL import Image
import io
from scipy.ndimage import label
from src.geometry.thresholds_loader import load_thresholds_config

def get_largest_cc(binary_mask):
    labeled, num_features = label(binary_mask)
    if num_features == 0:
        return None
    counts = np.bincount(labeled.flat)[1:]
    largest = np.argmax(counts) + 1
    return labeled == largest

def min_area_rect(points):
    """
    Computes minAreaRect using PCA on points (N x 2 array of y, x).
    Returns (width, height, angle).
    """
    if len(points) == 0:
        return 0, 0
    # Centering
    center = np.mean(points, axis=0)
    pts = points - center
    
    # Covariance matrix
    cov = np.cov(pts, rowvar=False)
    # Eigen decomposition
    evals, evecs = np.linalg.eigh(cov)
    
    # Project points onto eigenvectors
    # evecs is 2x2. evecs[:, 0] and evecs[:, 1] are the axes
    proj1 = pts.dot(evecs[:, 0])
    proj2 = pts.dot(evecs[:, 1])
    
    extent1 = np.max(proj1) - np.min(proj1)
    extent2 = np.max(proj2) - np.min(proj2)
    
    # points are [y, x], so evecs[:, i] is [dy, dx]
    # The width of the upright label aligns more with the X-axis.
    if abs(evecs[1, 0]) > abs(evecs[0, 0]):
        width = float(extent1)
        height = float(extent2)
    else:
        width = float(extent2)
        height = float(extent1)
        
    return width, height

def otsu_threshold(arr):
    # Otsu's method
    hist, _ = np.histogram(arr.flat, bins=256, range=(0, 256))
    total = arr.size
    
    sum_total = np.sum(np.arange(256) * hist)
    
    weight_b = 0.0
    sum_b = 0.0
    var_max = 0.0
    threshold = 0
    
    for t in range(256):
        weight_b += hist[t]
        if weight_b == 0:
            continue
            
        weight_f = total - weight_b
        if weight_f == 0:
            break
            
        sum_b += t * hist[t]
        
        mean_b = sum_b / weight_b
        mean_f = (sum_total - sum_b) / weight_f
        
        var_between = weight_b * weight_f * (mean_b - mean_f) ** 2
        
        if var_between > var_max:
            var_max = var_between
            threshold = t
            
    return threshold

def calibrate_photo(image, label_width_mm, word_index=None):
    """
    Returns {"scale": ..., "sigma": ..., "pdp_area_cm2": ...} 
    or {"error": reason_code, "message": "..."}
    """
    if not label_width_mm:
        return {"error": "NO_SCALE_REFERENCE", "message": "No scale reference provided"}
        
    config = load_thresholds_config()
    
    if isinstance(image, bytes):
        image = Image.open(io.BytesIO(image))
        
    # 1. Otsu threshold + largest connected component
    gray = image.convert('L')
    arr = np.array(gray)
    thresh = otsu_threshold(arr)
    # Background is usually lighter or darker. Let's assume object is in center and differs from edges.
    # To be generic, let's just use arr < thresh. If the background is dark, this might invert.
    # Usually labels are lighter than dark backgrounds, or vice versa.
    # A simple way is to check the corners.
    corners = [arr[0,0], arr[0,-1], arr[-1,0], arr[-1,-1]]
    bg_color = np.median(corners)
    if bg_color > thresh:
        binary = arr <= thresh # object is dark
    else:
        binary = arr > thresh # object is light
        
    blob = get_largest_cc(binary)
    if blob is None:
        return {"error": "UNREADABLE_IMAGE", "message": "Could not segment the label"}
        
    # 2. minAreaRect
    y, x = np.nonzero(blob)
    points = np.column_stack((y, x))
    if len(points) == 0:
        return {"error": "UNREADABLE_IMAGE", "message": "Invalid label shape"}
        
    center = np.mean(points, axis=0)
    pts = points - center
    cov = np.cov(pts, rowvar=False)
    evals, evecs = np.linalg.eigh(cov)
    
    proj1 = pts.dot(evecs[:, 0])
    proj2 = pts.dot(evecs[:, 1])
    
    extent1 = float(np.max(proj1) - np.min(proj1))
    extent2 = float(np.max(proj2) - np.min(proj2))
    
    w_px = max(extent1, extent2)
    h_px = min(extent1, extent2)
    
    if w_px == 0 or h_px == 0:
        return {"error": "UNREADABLE_IMAGE", "message": "Invalid label shape"}
        
    # Check if aspect ratio is near 1:1, return NA
    if (w_px / h_px) < 1.1:
        return {"error": "AMBIGUOUS_ORIENTATION", "message": "Aspect ratio near 1:1, cannot map physical width to axis"}
        
    # Map label_width_mm to the PCA axis parallel to text reading direction if word_index is present
    if word_index:
        word_w = [w["box"]["width"] for w in word_index if "box" in w and w["box"]]
        word_h = [w["box"]["height"] for w in word_index if "box" in w and w["box"]]
        if word_w and word_h:
            median_w = np.median(word_w)
            median_h = np.median(word_h)
            # If text is rotated 90 degrees, characters/boxes are taller than they are wide.
            # Usually text boxes are horizontal (wider). If they are vertical, image is rotated.
            # If rotated, the physical width (horizontal to text) corresponds to the vertical PCA axis in the image!
            is_rotated = median_h > median_w
            
            # The PCA axis most vertical in the image is the one with larger Y component
            vert_extent = extent1 if abs(evecs[0, 0]) > abs(evecs[1, 0]) else extent2
            horz_extent = extent2 if abs(evecs[0, 0]) > abs(evecs[1, 0]) else extent1
            
            # So if rotated, physical width = vert_extent. If upright, physical width = horz_extent.
            physical_width_px = vert_extent if is_rotated else horz_extent
        else:
            # Fallback to horizontal extent if no boxes
            physical_width_px = extent1 if abs(evecs[1, 0]) > abs(evecs[0, 0]) else extent2
    else:
        # Default: physical width maps to the horizontal extent in the image frame
        physical_width_px = extent1 if abs(evecs[1, 0]) > abs(evecs[0, 0]) else extent2

    # 3. Rectangularity gate
    blob_area = np.sum(blob)
    rect_area = extent1 * extent2
    rectangularity = blob_area / rect_area
    if rectangularity < config["rectangularity_min"]:
        return {"error": "SHADOW_MERGE", "message": "Label rectangularity too low. Ensure plain background and no harsh shadows."}
        
    # 4. Tilt
    y_sorted = np.sort(points[:, 0])
    x_sorted = np.sort(points[:, 1])
    
    # 5. Scale and Sanity
    scale = physical_width_px / label_width_mm # px per mm
    
    if scale < config["resolution_min_px_per_mm"]:
        return {"error": "LOW_RESOLUTION", "message": "Image resolution too low"}
        
    # Implausibility sanity check: implied median body-text height 0.5-4.0mm
    if word_index:
        heights = []
        for w in word_index:
            if "box" in w and w["box"]:
                # If rotated, the text height is the box width
                is_word_rotated = w["box"]["height"] > w["box"]["width"]
                true_h_px = w["box"]["width"] if is_word_rotated else w["box"]["height"]
                heights.append(true_h_px)
        if heights:
            median_h_px = np.median(heights)
            median_h_mm = median_h_px / scale
            if median_h_mm < 0.5 or median_h_mm > 4.0:
                return {"error": "IMPLAUSIBLE_SCALE", "message": "Calibration sanity check failed: text height out of bounds"}
        
    # 6. PDP area
    physical_height_px = extent2 if physical_width_px == extent1 else extent1
    label_height_mm = physical_height_px / scale
    pdp_area_cm2 = (label_width_mm / 10.0) * (label_height_mm / 10.0)
    
    # error budget sigma = 5%
    sigma = 0.05
    
    return {
        "scale": float(scale),
        "sigma": float(sigma),
        "pdp_area_cm2": float(pdp_area_cm2)
    }
