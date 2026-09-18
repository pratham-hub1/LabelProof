import pytest
import json
from src.reports.csv import build_csv_report, build_json_report

def test_build_csv_report():
    results = {
        "R1": {"name": "Rule 1", "status": "PASS", "evidence": "good", "anchored": True},
        "R2": {"name": "Rule 2", "status": "FAIL", "evidence": {"val": 10}, "fix": "fix it", "anchored": False}
    }
    summary = {
        "found_declarations": 5,
        "pass": 1,
        "fail": 1,
        "na": 0,
        "needs_review": 0,
        "exempt": 0
    }
    
    csv_bytes = build_csv_report(results, summary)
    assert csv_bytes.startswith(b'\xef\xbb\xbf')
    text = csv_bytes.decode('utf-8-sig')
    
    assert "Rule 1" in text
    assert '""val"": 10' in text
    assert "Found 5 declarations" in text

def test_build_json_report():
    record = {"scan_id": "SC-123", "status": "DONE"}
    json_bytes = build_json_report(record)
    data = json.loads(json_bytes.decode('utf-8'))
    assert data["scan_id"] == "SC-123"
