from src.rules.patterns_loader import load_patterns_config

def test_load_patterns_config():
    config = load_patterns_config()
    assert "r1" in config
    assert "pin_regex" in config["r1"]
    assert "r5" in config
    assert "(inclusive of all taxes)" in config["r5"]["taxes_clauses"]
    assert "r11" in config
    assert "minimum" in config["r11"]["qualifiers"]
    assert len(config["r11"]["third_schedule"]) == 26
