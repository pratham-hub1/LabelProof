import os
import json
from src.gauntlet.anchors_loader import load_anchors_config

def test_load_anchors_config(tmp_path):
    # Test loading from a specific path
    test_config = {
        "mrp": ["\\bMRP\\b"]
    }
    
    config_file = tmp_path / "anchors.config"
    config_file.write_text(json.dumps(test_config))
    
    anchors = load_anchors_config(str(config_file))
    assert "mrp" in anchors
    assert len(anchors["mrp"]) == 1
    assert anchors["mrp"][0] == "\\bMRP\\b"

def test_load_anchors_config_default():
    # Test loading from the default path (should not fail)
    anchors = load_anchors_config()
    assert "mrp" in anchors
    assert "net_quantity" in anchors
    assert "mfg_date" in anchors
    assert "consumer_care" in anchors
