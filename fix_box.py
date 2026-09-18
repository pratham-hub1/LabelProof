import sys

files = [
    "backend/src/gauntlet/gates/g1.py",
    "backend/src/geometry/measure.py",
    "backend/src/geometry/check_r10.py"
]

for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    content = content.replace("left, top, right, bottom = box", '''if isinstance(box, dict):
        left, top = box.get("left", 0), box.get("top", 0)
        right, bottom = left + box.get("width", 0), top + box.get("height", 0)
    else:
        left, top, right, bottom = box''')
        
    with open(file, "w") as f:
        f.write(content)
