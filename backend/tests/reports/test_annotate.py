import pytest
from PIL import Image
from src.reports.annotate import render_annotated

def test_render_annotated():
    canonical_image = Image.new('RGB', (800, 600), color='white')
    results = {
        "R1": {"status": "PASS", "box": {"ymin": 0.1, "xmin": 0.1, "ymax": 0.2, "xmax": 0.2}},
        "R2": {"status": "FAIL", "box": {"ymin": 0.3, "xmin": 0.3, "ymax": 0.4, "xmax": 0.4}},
        "R3": {"status": "NA", "box": {"ymin": 0.5, "xmin": 0.5, "ymax": 0.6, "xmax": 0.6}},
        "R4": {"status": "NEEDS_REVIEW", "box": {"ymin": 0.7, "xmin": 0.7, "ymax": 0.8, "xmax": 0.8}},
        "R5": {"status": "PASS"}, # no box
        "R6": {"status": "PASS", "box": {"ymin": -0.1, "xmin": 0.1, "ymax": 0.2, "xmax": 0.2}}, # out of bounds
        "R7": {"status": "PASS", "box": {"ymin": 0.1, "xmin": 0.1, "ymax": 0.2, "xmax": 0.2}}, # grouped with R1
    }
    exemption = {"applied": False}
    summary = {"pass": 2, "fail": 1, "na": 1, "needs_review": 1}
    config = {
        "colors": {
            "PASS": "#00FF00",
            "FAIL": "#FF0000",
            "NEEDS_REVIEW": "#FFA500",
            "NA": "#FFA500",
            "EXEMPT": "#808080"
        }
    }
    
    img = render_annotated(canonical_image, results, exemption, summary, config)
    assert img.size[0] == 800
    assert img.size[1] > 600 # banner prepended

def test_render_annotated_exempt():
    canonical_image = Image.new('RGB', (800, 600), color='white')
    results = {}
    exemption = {"applied": True, "rule": "Rule 26(a)"}
    summary = {"exempt": 1}
    config = {"colors": {"EXEMPT": "#808080"}}
    
    img = render_annotated(canonical_image, results, exemption, summary, config)
    assert img.size[0] == 800
    assert img.size[1] > 600
