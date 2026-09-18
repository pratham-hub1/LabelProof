import pytest
import os
import json
from benchmark.score import score_record
from benchmark.report import clopper_pearson, generate_benchmark_report
from benchmark.disputes import load_ground_truth

def test_f8_criteria_3_boundary_r8():
    # Boundary R8 truth excluded from accuracy but kept in coverage
    # PDP area 100cm2 -> threshold is 4.0mm
    truth = {
        'label_id': 'L1',
        'source_type': 'photo',
        'measured_width_mm': 100,
        'pdp_width_mm': 100,
        'pdp_height_mm': 1000,
        'numeral_heights_mm': {'net_quantity': 3.9},
        'fields': {},
        'expected_verdicts': {'R8': 'FAIL'}
    }
    
    result = {'results': {'R8': {'status': 'FAIL'}}}
    
    score = score_record(result, truth)
    assert score['r8_boundary_skip'] is True
    
    metrics, md = generate_benchmark_report([score], {})
    assert metrics['coverage']['value'] == 1.0 # Kept in coverage
    assert 'R8' not in metrics['accuracy_by_rule'] # Excluded from accuracy


def test_f8_criteria_8_skip_cache():
    # BENCHMARK_SKIP_CACHE default off asserted by fixture
    assert os.environ.get('BENCHMARK_SKIP_CACHE', '0') == '0'

def test_f8_clopper_pearson():
    lower, upper = clopper_pearson(50, 100)
    assert 0.39 < lower < 0.41
    assert 0.59 < upper < 0.61
    
    # Coverage logic
    metrics, md = generate_benchmark_report([
        {'label_id': 'L1', 'matches': {'R1': {'correct': True}, 'R8': {'correct': False}}, 'r8_boundary_skip': False}
    ], {})
    
    assert 'Coverage' in md
