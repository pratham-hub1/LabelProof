import pytest
from src.reports.summary import compute_found_declarations, compute_summary_counts

def test_compute_found_declarations():
    field_status = {
        "manufacturer_name": "VERIFIED",
        "manufacturer_address": "ABSENT",
        "generic_name": "VERIFIED",
        "net_quantity": "VERIFIED",
        "mrp": "VERIFIED",
        "mfg_date": "VERIFIED",
        "consumer_care": "ABSENT",
        "some_other_field": "VERIFIED"
    }
    assert compute_found_declarations(field_status) == 5

def test_compute_summary_counts():
    results = {
        "R1": {"status": "PASS"},
        "R2": {"status": "FAIL"},
        "R3": {"status": "NA"},
        "R4": {"status": "NEEDS_REVIEW"},
        "R5": {"status": "PASS"},
    }
    counts = compute_summary_counts(results)
    assert counts['pass'] == 2
    assert counts['fail'] == 1
    assert counts['na'] == 1
    assert counts['needs_review'] == 1
    assert counts['exempt'] == 0

    counts_exempt = compute_summary_counts(results, is_exempt=True)
    assert counts_exempt['exempt'] == 1
