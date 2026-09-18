import json
import jsonschema
import os

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'ground_truth.schema.json')

def load_ground_truth(filepath: str) -> list:
    """
    Loads and validates the ground truth JSON against the schema.
    """
    with open(SCHEMA_PATH, 'r') as sf:
        schema = json.load(sf)
        
    with open(filepath, 'r') as f:
        data = json.load(f)
        
    jsonschema.validate(instance=data, schema=schema)
    return data

def export_disputes(scored_records: list, out_path: str):
    """
    Exports disagreements between system and ground truth for adjudication.
    """
    disputes = []
    for rec in scored_records:
        disagreements = {}
        for rule, data in rec['matches'].items():
            if not data['correct']:
                disagreements[rule] = {
                    'expected': data['expected'],
                    'system': data['system']
                }
        if disagreements:
            disputes.append({
                'label_id': rec['label_id'],
                'disagreements': disagreements
            })
            
    with open(out_path, 'w') as f:
        json.dump(disputes, f, indent=2)
