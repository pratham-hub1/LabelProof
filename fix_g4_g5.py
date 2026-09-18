import sys

files = [
    "backend/src/gauntlet/gates/g4.py",
    "backend/src/gauntlet/gates/g5.py"
]

for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    content = content.replace("left, top, right, bottom = box", '''if isinstance(box, dict):
        left, top = box.get("left", 0), box.get("top", 0)
        right, bottom = left + box.get("width", 0), top + box.get("height", 0)
    else:
        left, top, right, bottom = box''')
        
    content = content.replace("w_left, w_top, w_right, w_bottom = wb", '''if isinstance(wb, dict):
            w_left, w_top = wb.get("left", 0), wb.get("top", 0)
            w_right, w_bottom = w_left + wb.get("width", 0), w_top + wb.get("height", 0)
        else:
            w_left, w_top, w_right, w_bottom = wb''')

    with open(file, "w") as f:
        f.write(content)
