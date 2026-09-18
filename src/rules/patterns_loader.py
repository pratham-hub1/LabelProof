import json
import os

def load_patterns_config(config_path=None):
    if config_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "patterns.config")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
