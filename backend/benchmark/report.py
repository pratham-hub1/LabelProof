import json
import scipy.stats

def clopper_pearson(k, n, alpha=0.05):
    """
    Computes the Clopper-Pearson exact binomial confidence interval.
    k: successes
    n: trials
    alpha: significance level (0.05 for 95% CI)
    """
    if n == 0:
        return 0.0, 0.0
    lower = scipy.stats.beta.ppf(alpha / 2, k, n - k + 1) if k > 0 else 0.0
    upper = scipy.stats.beta.ppf(1 - alpha / 2, k + 1, n - k) if k < n else 1.0
    return lower, upper

def generate_benchmark_report(scored_records: list, config: dict):
    """
    Generates Markdown and JSON benchmark reports.
    """
    rules = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'R7', 'R8', 'R9', 'R10', 'R11']
    
    metrics = {r: {'correct': 0, 'total': 0} for r in rules}
    coverage = {'covered': 0, 'total': len(scored_records)}
    
    for rec in scored_records:
        matches = rec['matches']
        all_rules_evaluated = True
        
        for rule, data in matches.items():
            # R8 Boundary exclusion
            if rule == 'R8' and rec.get('r8_boundary_skip'):
                continue
                
            metrics[rule]['total'] += 1
            if data['correct']:
                metrics[rule]['correct'] += 1
            else:
                all_rules_evaluated = False
                
        # Coverage: Did it process successfully without INTERNAL/EXTRACTION_FAILED errors?
        # Actually F8 says "expected 85-95% coverage". So if it yielded a verdict for all expected rules, it's covered.
        if all_rules_evaluated:
            coverage['covered'] += 1
            
    json_out = {
        'coverage': {
            'value': coverage['covered'] / coverage['total'] if coverage['total'] else 0,
            'ci': clopper_pearson(coverage['covered'], coverage['total'])
        },
        'accuracy_by_rule': {}
    }
    
    md_lines = [
        "# Benchmark Report",
        "",
        f"**Coverage:** {coverage['covered']}/{coverage['total']} ({json_out['coverage']['value']:.1%})",
        f"**95% CI:** [{json_out['coverage']['ci'][0]:.1%}, {json_out['coverage']['ci'][1]:.1%}]",
        "",
        "## Accuracy by Rule",
        "| Rule | Accuracy | 95% CI |",
        "|---|---|---|"
    ]
    
    for rule in rules:
        if metrics[rule]['total'] > 0:
            k = metrics[rule]['correct']
            n = metrics[rule]['total']
            acc = k / n
            ci = clopper_pearson(k, n)
            json_out['accuracy_by_rule'][rule] = {
                'value': acc,
                'ci': ci,
                'n': n
            }
            md_lines.append(f"| {rule} | {acc:.1%} ({k}/{n}) | [{ci[0]:.1%}, {ci[1]:.1%}] |")
            
    return json_out, "\n".join(md_lines)
