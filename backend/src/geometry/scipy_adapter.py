import cv2
import numpy as np

def label(input_array, structure=None):
    if input_array.dtype == bool:
        img = input_array.astype(np.uint8)
    else:
        img = input_array.astype(np.uint8)
    
    num_labels, labels = cv2.connectedComponents(img, connectivity=4)
    num_features = num_labels - 1 if num_labels > 0 else 0
    return labels, num_features

def find_objects(input_array, max_label=0):
    n_features = int(input_array.max())
    if max_label > 0:
        n_features = min(n_features, max_label)
        
    objects = []
    for i in range(1, n_features + 1):
        mask = (input_array == i).astype(np.uint8)
        if cv2.countNonZero(mask) == 0:
            objects.append(None)
            continue
        x, y, w, h = cv2.boundingRect(mask)
        objects.append((slice(y, y + h, None), slice(x, x + w, None)))
        
    return objects
