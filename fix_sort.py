import sys

files = [
    "backend/src/gauntlet/gates/g4.py",
    "backend/src/gauntlet/gates/g5.py"
]

for file in files:
    with open(file, "r") as f:
        content = f.read()
    
    content = content.replace('inside_words.sort(key=lambda x: (x["box"][1], x["box"][0]))', '''def get_top_left(x):
        b = x["box"]
        if isinstance(b, dict):
            return b.get("top", 0), b.get("left", 0)
        return b[1], b[0]
    inside_words.sort(key=get_top_left)''')
    
    with open(file, "w") as f:
        f.write(content)
