import json
import os

def load_anchors_config(config_path=None):
    """
    Loads the anchors.config file into a dictionary mapping fields to regex patterns.
    """
    if config_path is None:
        # Default to the config file in the project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "anchors.config")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
