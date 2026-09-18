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
            if status not in ["VERIFIED", "ABSENT"]:
                results[rule_id] = {
                    "status": "NA",
                    "reason_code": "DEPENDENCY_UNAVAILABLE",
                    "message": f"Dependency {req_field} is {status}"
                }
                missing_dep = True
                break
                
        if not missing_dep:
            try:
                results[rule_id] = check_meta["func"](context)
            except Exception as e:
                # Fallback if a check raises unexpectedly, though they should be pure
                results[rule_id] = {
                    "status": "NEEDS_REVIEW",
                    "reason_code": "CHECK_ERROR",
                    "message": str(e)
                }
                
    return results
