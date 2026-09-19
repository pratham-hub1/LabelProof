class CheckRegistry:
    def __init__(self):
        self.checks = {}
        
    def register(self, rule_id, requires=None):
        def decorator(func):
            self.checks[rule_id] = {
                "func": func,
                "requires": requires or []
            }
            return func
        return decorator

registry = CheckRegistry()

# Explicitly register all 11 checks
from src.rules.checks import r1, r2, r3, r4, r5, r6_r11, r7, r8, r9, r10

def run_checks(context):
    """
    Runs all registered checks.
    context = {
        "extraction": ...,
        "word_index": ...,
        "field_status": ...,
        "readability": ...,
        "config": ...
    }
    Returns a dict mapping rule_id -> CheckResult
    """
    results = {}
    field_status = context.get("field_status", {})
    
    for rule_id, check_meta in registry.checks.items():
        missing_dep = False
        for req_field in check_meta["requires"]:
            status = field_status.get(req_field)
            if status != "VERIFIED":
                results[rule_id] = {
                    "status": "NA",
                    "reason_code": "DEPENDENCY_UNAVAILABLE",
                    "message": f"Dependency {req_field} is {status}"
                }
                missing_dep = True
                break
                
        if not missing_dep:
            results[rule_id] = check_meta["func"](context)
                
    return results
