import csv
import io
import json

def build_csv_report(results: dict, summary: dict) -> bytes:
    """
    Builds a CSV report.
    RFC 4180 quoting, UTF-8 with BOM.
    Header + one row per result + summary row.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, dialect='excel') # excel is RFC 4180 compliant
    
    # Header
    writer.writerow(["Rule ID", "Name", "Status", "Evidence", "Fix", "Anchored"])
    
    # Results
    for rule_id, res in results.items():
        evidence = res.get('evidence', '')
        if isinstance(evidence, (dict, list)):
            evidence = json.dumps(evidence)
        elif res.get('measurement'):
            evidence = json.dumps(res.get('measurement'))
            
        writer.writerow([
            rule_id,
            res.get('name', ''),
            res.get('status', 'NA'),
            evidence,
            res.get('fix', ''),
            str(res.get('anchored', ''))
        ])
        
    # Summary Row
    writer.writerow([])
    writer.writerow(["SUMMARY", f"Found {summary.get('found_declarations', 0)} declarations", 
                     f"PASS: {summary.get('pass', 0)}", 
                     f"FAIL: {summary.get('fail', 0)}", 
                     f"NA: {summary.get('na', 0)}", 
                     f"NEEDS_REVIEW: {summary.get('needs_review', 0)}",
                     f"EXEMPT: {summary.get('exempt', 0)}"])
                     
    # Encode with UTF-8 BOM
    return b'\xef\xbb\xbf' + buffer.getvalue().encode('utf-8')

def build_json_report(record: dict) -> bytes:
    """
    Serializes the final scan record to JSON bytes.
    """
    return json.dumps(record, indent=2, sort_keys=True).encode('utf-8')
