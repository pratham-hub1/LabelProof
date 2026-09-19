import os
import json

def score_record(result: dict, truth: dict) -> dict:
    """
    Computes accuracy and coverage metrics for a single label.
    Takes the system's final result record and the ground truth.
    Returns a dict with per-rule matching status and flags.
    """
    res = result.get('results', {})
    expected = truth.get('expected_verdicts', {})
    
    # Stratifications
    is_hindi = truth.get('fields', {}).get('is_hindi', False)
    source_type = truth.get('source_type', 'photo')
    
    # Boundary logic for R8
    numeral_heights = truth.get('numeral_heights_mm', {})
    r8_boundary_skip = False
    
    if 'R8' in expected:
        # Simplistic boundary check: F8 says +-0.3mm of threshold.
        # R8 threshold depends on PDP area. For testing, we just check if it's explicitly marked or we compute it.
        # Since score.py shouldn't replicate rule logic fully, we can check if it's between say 3.7 and 4.3 or 5.7 and 6.3.
        # Actually F8 says "measured within +-0.3mm of the threshold".
        # Let's say we compute the area and get the threshold.
        try:
            from src.geometry.check_r8 import get_required_mm_candidates
        except ModuleNotFoundError:
            import sys
            sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))
            from src.geometry.check_r8 import get_required_mm_candidates
        
        import json
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'thresholds.config')
        try:
            with open(config_path) as f:
                r7_table = json.load(f)["rule7_table"]
        except Exception as e:
            print(f"Error loading thresholds.config: {e}")
            r7_table = [
                {"max_area": 50, "normal": 1.0, "molded": 1.5},
                {"max_area": 100, "normal": 1.5, "molded": 3.0},
                {"max_area": 500, "normal": 2.5, "molded": 4.0},
                {"max_area": 2500, "normal": 4.0, "molded": 6.0},
                {"max_area": 999999999, "normal": 6.0, "molded": 6.0}
            ]
            
        pdp_width = truth.get('pdp_width_mm', 0)
        pdp_height = truth.get('pdp_height_mm', 0)
        pdp_area = (pdp_width * pdp_height) / 100 # cm2
        r_min, r_max = get_required_mm_candidates(pdp_area, False, r7_table, 0.0)
        print("R_MIN IS", r_min, r_max)
        req_height = r_min
        
        # Check if any measured height is within 0.3 of req_height
        for k, h in numeral_heights.items():
            if abs(h - req_height) <= 0.3:
                r8_boundary_skip = True
                break
    
    match_dict = {}
    
    for rule, exp in expected.items():
        sys_status = res.get(rule, {}).get('status', 'NA')
        match_dict[rule] = {
            'expected': exp,
            'system': sys_status,
            'correct': sys_status == exp
        }
        
    return {
        'label_id': truth.get('label_id'),
        'matches': match_dict,
        'is_hindi': is_hindi,
        'source_type': source_type,
        'r8_boundary_skip': r8_boundary_skip
    }
