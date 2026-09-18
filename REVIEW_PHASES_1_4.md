# REVIEW_PHASES_1_4.md

## Verdict: BLOCKED (13 Findings)

The system currently violates the core principle of model-independent correctness in several places, primarily by emitting false FAIL verdicts on uncertain fields or unreadable images. There are also critical missing validations, test failures, and geometry engine flaws. The review is BLOCKED from proceeding to Phase 5 until these findings are fixed.

## Findings

### B1: Rule engine bypasses dependency framework causing wrong FAILs (R1)
- **File:** `src/rules/checks/r1.py:4`
- **Severity:** Blocker (Core principle violation)
- **Spec violated:** F3 §3.2 (Missing-vs-unreadable lock) & F3 §3.3 (Dependency declaration)
- **Evidence:** Running `probe_core.py` with `manufacturer_address: UNREADABLE` outputs:
  `"r1_unreadable":{"fix":"print the manufacturer's name and address","status":"FAIL"}`
- **Fix:** The check registers with `requires=[]`. It must declare `requires=["manufacturer_name", "manufacturer_address"]` so the engine short-circuits `UNREADABLE` to `NA (DEPENDENCY_UNAVAILABLE)`. Then handle `ABSENT` explicitly within the check.

### B2: R2 (Generic Name) emits false FAIL for unreadable fields
- **File:** `src/rules/checks/r2.py:3`
- **Severity:** Blocker (Core principle violation)
- **Spec violated:** F3 §3.3 (R2 spec: UNREADABLE -> NA)
- **Evidence:** `probe_core.py` with `generic_name: UNREADABLE` outputs:
  `"r2_unreadable":{"fix":"print the commodity's common/generic name","status":"FAIL"}`
- **Fix:** Declare `requires=["generic_name"]` in the registry and handle `ABSENT` manually, letting the engine short-circuit `UNREADABLE`.

### B3: R6 (Consumer Care) emits false FAIL for unreadable fields
- **File:** `src/rules/checks/r6_r11.py:3`
- **Severity:** Blocker (Core principle violation)
- **Spec violated:** F3 §3.3 (R6 spec: UNREADABLE -> NA)
- **Evidence:** `probe_core.py` with `consumer_care: UNREADABLE` outputs:
  `"r6_unreadable":{"fix":"no contactable channel","status":"FAIL"}`
- **Fix:** Declare `requires=["consumer_care"]` and handle `ABSENT`.

### B4: R11 improperly broadens scope by appending generic name
- **File:** `src/rules/checks/r6_r11.py:42`
- **Severity:** Blocker (False FAIL risk)
- **Spec violated:** F3 §3.3 (R11 spec: "Scope: the quantity declaration's raw text ONLY")
- **Evidence:** `check_r11` uses `text_to_check = (nq_raw + " " + gn_raw).lower()`. If generic name is "All About Nuts", it triggers the "about" qualifier.
- **Fix:** Only check `nq_raw` against the qualifiers list.

### B5: R3 sub-kilogram rule incorrectly passes values < 1 kg/l
- **File:** `src/rules/checks/r3.py:15`
- **Severity:** Blocker (False PASS)
- **Spec violated:** F3 §3.3 (R3 spec: Value < 1 with unit kg/l ("0.5 kg") -> FAIL)
- **Evidence:** `probe_core.py` with value `0.5 kg` outputs:
  `"r3_sub_kg":{"status":"PASS"}`
- **Fix:** Add a check in `check_r3` that returns `FAIL` if `val < 1` and `unit in ["kg", "l"]`.

### B6: R5 (MRP) violates deterministic multiple-instance sweep and shorthand rules
- **File:** `src/rules/checks/r5.py:17-19, 27`
- **Severity:** Blocker (Spec violation)
- **Spec violated:** F3 §3.3 (R5 spec)
- **Evidence:** 
  1. `probe_core.py` with two MRP instances in the raw string outputs `"r5_multiple":{"fix":"taxes clause is unambiguous in law","status":"FAIL"}` (should be `NEEDS_REVIEW`).
  2. `probe_core.py` with "MRP Rs. 20 (inclusive of all taxes)" outputs `"r5_shorthand_taxes":{"status":"PASS"}` (should be `NEEDS_REVIEW`).
- **Fix:** 
  1. Use the full word index sweep to detect multiple distinct instances of price values across anchored regions, rather than just counting "Rs" in the raw text.
  2. Check for "MRP" shorthand vs full wording and return `NEEDS_REVIEW` appropriately.

### B7: Geometry Engine incorrectly measures character heights via axis-aligned bounding boxes
- **File:** `src/geometry/measure.py:46`
- **Severity:** Blocker (Feature 2 failure)
- **Spec violated:** F2 (Rotated labels support)
- **Evidence:** `probe_rotation.py` output on numerals rotated 90 degrees (`numerals_90`) gives a `measured_height_px` of `21.0` while `numerals_0` gives `61.0`. The engine uses `scipy.ndimage.find_objects` (AABBs), causing width to be measured as height on rotation.
- **Fix:** Extract individual digits and compute minAreaRect (PCA extents) to get rotation-invariant heights.

### B8: `test_exemptions.py` is broken and untended
- **File:** `tests/rules/test_exemptions.py`
- **Severity:** Blocker (Test Suite Failure)
- **Evidence:** 
  `TypeError: evaluate_exemptions() missing 1 required positional argument: 'tobacco_config'`
- **Fix:** Update the test to pass `tobacco_config` and check the dictionary return format (`{"status": "EXEMPT", ...}`).

### B9: G1 Box Sanity Check accepts partially out-of-bounds boxes
- **File:** `src/gauntlet/gates/g1.py:21-25`
- **Severity:** Blocker (Feature 1 spec)
- **Spec violated:** F1 §1.4 ("inside image bounds")
- **Evidence:** `probe_malformed.py` output for G1 shows `"partial_left":true` and `"partial_right":true`.
- **Fix:** Change bounding box checks to ensure `left >= 0`, `top >= 0`, `right <= img_w`, and `bottom <= img_h`.

### B10: G3 Parsed <-> Raw Consistency Check is vulnerable to substring attacks
- **File:** `src/gauntlet/gates/g3.py:31, 45`
- **Severity:** Blocker
- **Spec violated:** F1 §1.4 (Parsed values must map exactly)
- **Evidence:** `probe_malformed.py` output for G3 shows `"split_digits":true` and `"unit_substring":true`. "123" matches "12 3", and unit "g" matches inside "Great".
- **Fix:** Ensure numeric digit sequences match contiguously and units use word-boundary matching `\b`.

### B11: G4 Crop-verify fails to enforce exact numerals sequence
- **File:** `src/gauntlet/gates/g4.py:75`
- **Severity:** Blocker (Feature 1 spec)
- **Spec violated:** F1 §1.4 ("numerals must match exactly in sequence")
- **Evidence:** `probe_malformed.py` for G4 outputs `"substring":true`. The code uses `norm_raw in norm_ocr`, allowing "12" to match inside "123".
- **Fix:** Implement sequence-specific matching that ensures numbers are fully bounded and not substrings of other numbers.

### B12: G6 Confidence gate crashes on malformed claim values
- **File:** `src/gauntlet/gates/g6.py:13`
- **Severity:** Blocker (Stability)
- **Evidence:** `probe_malformed.py` for G6 outputs: `TypeError: float() argument must be a string or a real number, not 'dict'`.
- **Fix:** Use a catch-all `except (ValueError, TypeError)` when parsing confidence.

### B13: Geometry Engine calibration missing 0.5-4.0 mm sanity check
- **File:** `src/geometry/calibrate.py:145`
- **Severity:** Blocker
- **Spec violated:** F2 ("sanity 0.5-4.0 mm")
- **Evidence:** The file has a comment `# Implausibility sanity check: implied median body-text height 0.5-4.0mm ... Let's assume sanity check is done externally ...` but it is never implemented in the pipeline.
- **Fix:** Implement the 0.5-4.0mm sanity check by computing the median height of all word index bounding boxes.

## OWNER QUESTIONS
1. **Geometry Area Constraints:** Is the PCA extents calculation on connected components sufficient for handling wildly rotated or warped labels, or do we require projective transformation unwrapping first?
2. **Exemption Extensibility:** Rule 3(b) and other non-detectable exemptions are currently excluded from the MVP. Should the schema explicitly reserve fields for future ML classification, or rely strictly on human reviewers?
3. **Word Index Dependency in Calibration:** `calibrate_photo` requires median text height for the 0.5-4.0mm sanity check, but it does not currently receive the `word_index`. Should we pass `word_index` to `calibrate_photo`?

## Test-Coverage Gaps
- **Missing Classification-rate Bar test:** There are no tests enforcing the F3 §3.8 criteria #2: "Classification-rate bar: on 20 clean fixtures, >= 85% of applicable checks return a definitive verdict".
- **Bypassed Logic:** The suite only tests happy paths for dependencies. R1, R2, and R6 missing required declarations hides their bugs.

## Reproduction Commands
To see test failures:
```bash
.venv\Scripts\python.exe -m pytest -v
```

To run probe scripts (and reproduce B1-B6, B9-B12):
```bash
.venv\Scripts\python.exe scratch\review_probe\probe_core.py
.venv\Scripts\python.exe scratch\review_probe\probe_malformed.py
.venv\Scripts\python.exe scratch\review_probe\probe_rotation.py
```
