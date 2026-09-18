import numpy as np
from PIL import Image, ImageDraw
from src.geometry.calibrate import otsu_threshold, get_largest_cc

def create_synthetic_image(width, height, rect_w, rect_h, add_shadow=False):
    img = Image.new('L', (width, height), color=255) # white bg
    draw = ImageDraw.Draw(img)
    left = (width - rect_w) // 2
    top = (height - rect_h) // 2
    draw.rectangle([left, top, left + rect_w - 1, top + rect_h - 1], fill=100)
    return img

img = create_synthetic_image(300, 200, 250, 125)
arr = np.array(img)
thresh = otsu_threshold(arr)
print("Thresh:", thresh)

corners = [arr[0,0], arr[0,-1], arr[-1,0], arr[-1,-1]]
bg_color = np.median(corners)
print("BG Color:", bg_color)

if bg_color > thresh:
    binary = arr < thresh # object is dark
else:
    binary = arr > thresh # object is light
    
print("Binary true count:", np.sum(binary))
blob = get_largest_cc(binary)
print("Blob None?", blob is None)
if blob is not None:
    print("Blob true count:", np.sum(blob))
