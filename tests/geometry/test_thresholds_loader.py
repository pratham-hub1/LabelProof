from src.geometry.thresholds_loader import load_thresholds_config

def test_load_thresholds_config():
    config = load_thresholds_config()
    assert "rectangularity_min" in config
    assert config["rectangularity_min"] == 0.80
    assert "rule7_table" in config
    assert len(config["rule7_table"]) == 5
