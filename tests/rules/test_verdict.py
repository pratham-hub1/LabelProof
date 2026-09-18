import pytest
from src.rules.verdict import final_verdict

def test_final_verdict_done():
    field_statuses = {"f1": "VERIFIED", "f2": "NA_EXEMPT"}
    check_results = {"r1": {"status": "PASS"}, "r2": {"status": "NA"}}
    assert final_verdict(field_statuses, check_results) == "DONE"

def test_final_verdict_failed_absent():
    field_statuses = {"f1": "VERIFIED", "f2": "ABSENT"}
    check_results = {"r1": {"status": "PASS"}}
    assert final_verdict(field_statuses, check_results) == "FAILED"

def test_final_verdict_failed_check():
    field_statuses = {"f1": "VERIFIED"}
    check_results = {"r1": {"status": "FAIL"}}
    assert final_verdict(field_statuses, check_results) == "FAILED"

def test_final_verdict_needs_review_field():
    field_statuses = {"f1": "NEEDS_REVIEW"}
    check_results = {"r1": {"status": "PASS"}}
    assert final_verdict(field_statuses, check_results) == "NEEDS_REVIEW"

def test_final_verdict_needs_review_check():
    field_statuses = {"f1": "VERIFIED"}
    check_results = {"r1": {"status": "NEEDS_REVIEW"}}
    assert final_verdict(field_statuses, check_results) == "NEEDS_REVIEW"

def test_final_verdict_fail_overrides_review():
    field_statuses = {"f1": "NEEDS_REVIEW"}
    check_results = {"r1": {"status": "FAIL"}}
    assert final_verdict(field_statuses, check_results) == "FAILED"
