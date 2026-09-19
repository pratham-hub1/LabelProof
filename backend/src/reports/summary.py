DECLARATION_FIELDS = [
    "manufacturer_name",
    "manufacturer_address",
    "generic_name",
    "net_quantity",
    "mrp",
    "mfg_date",
    "consumer_care"
]

def compute_found_declarations(field_status: dict) -> int:
    """
    Returns the count of DECLARATION_FIELDS that have a status of VERIFIED.
    """
    count = 0
    for field in DECLARATION_FIELDS:
        if field_status.get(field) == "VERIFIED":
            count += 1
    return count

def compute_summary_counts(results: list, is_exempt: bool = False) -> dict:
    """
    Computes PASS, FAIL, NA, NEEDS_REVIEW, and EXEMPT counts from rule results.
    If is_exempt is True, all rules are NA, but for summary we count the scan as EXEMPT.
    """
    counts = {'pass': 0, 'fail': 0, 'na': 0, 'needs_review': 0, 'exempt': 1 if is_exempt else 0}
    for res in results:
        st = res.get('status', 'NA').lower()
        if st in counts:
            counts[st] += 1
    return counts
