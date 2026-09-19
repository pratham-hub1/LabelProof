# backend/docs/CHECKS.md — The 11 Codified Checks (Exact Spec) — BACKEND ONLY

**Purpose:** the exact, judge-defensible specification for every check — citation, pass/fail logic, edge cases, examples — compiled 1:1 from the proven decision tables in ENGINEERING.md (Features 1–4). Coding agents build against THIS document; benchmark ground-truth labelers label against ENGINEERING.md's decision tables (F2/F3/F4), which this document compiles 1:1 — per the F8 decision-log entry.

**Drift rule:** ENGINEERING.md's decision tables are the source of truth. If any line here contradicts ENGINEERING.md, ENGINEERING.md wins and this file must be fixed. This document invents no spec — it compiles the proven one.

**Doc scoping:** backend build document (DECISIONS.md §8) — backend agents only; the frontend track never reads this file.

**Scope of law:** checkable content = Chapter II, Rules 6–17 of the Legal Metrology (Packaged Commodities) Rules, 2011. Positioning: an assist / self-check tool — NOT a legally certified replacement for inspectors. The report footer always states: "This tool assumes non-exempt retail packaged goods."

---

## 0. Common machinery (applies to every check)

### 0.1 Result statuses

Every check returns exactly one of `PASS | FAIL | NA | NEEDS_REVIEW` (CONTRACTS.md §4 enums).

### 0.2 Field-status pre-resolution

Checks never handle missing/unreadable logic themselves — the framework resolves every field first:

| Status | Meaning |
|---|---|
| `VERIFIED` | passed all six gauntlet gates — the raw text is on the label |
| `ABSENT` | null everywhere AND readability = true AND no field-type anchor anywhere in the word index → fail-able (the missing-vs-unreadable lock) |
| `UNREADABLE` | readability = false → NA territory |
| `NEEDS_REVIEW` | claim present, verification inconclusive (e.g. LOW_CONFIDENCE) |
| `NA_EXEMPT` | the exemption layer removed this field from scope |

### 0.3 Readability score (deterministic)

R = (OCR word count ≥ 15) AND (mean OCR word confidence ≥ 0.65). Thresholds live in config, tuned on fixtures.

### 0.4 Missing vs unreadable (the decision table)

| Situation | Verdict |
|---|---|
| R true, field null everywhere (LLM + no anchor in word index) | confidently absent → **FAIL** "declaration not found on label" (a real violation) |
| R false (image too poor) | **NA** — UNREADABLE_IMAGE |
| claim present, crop-verify failed | **NA** — VERIFY_FAILED |
| all gates pass, confidence < 0.60 | **NEEDS_REVIEW** — LOW_CONFIDENCE |
| field text in Devanagari only (Tesseract hin insufficient) | **NEEDS_REVIEW** — UNSUPPORTED_LANGUAGE |
| no claim, R true, field-type anchor present in the word index | **NEEDS_REVIEW** — EXTRACTION_MISS | possible extraction miss; rescan suggested |

### 0.5 Dependencies

Each check declares the fields it requires. A required field not in `VERIFIED`/`ABSENT` status → the check returns **NA** with reason `DEPENDENCY_UNAVAILABLE` — distinct from "field absent" (that is a FAIL case).

### 0.6 Reason codes (first-class, always carried)

`NOT_PRINTED`, `UNREADABLE_IMAGE`, `VERIFY_FAILED`, `LOW_CONFIDENCE`, `UNSUPPORTED_LANGUAGE`, `NO_SCALE_REFERENCE`, `DEPENDENCY_UNAVAILABLE`, `NA_EXEMPT`, `EXTRACTION_MISS` — each with a human-readable message and a suggested action, all mapped in config, never hardcoded.

### 0.7 Fix texts

Every FAIL carries a concrete fix instruction; PASS/NA carry `null` (CONTRACTS.md §2). Fix texts live in config.

### 0.8 Exemption pre-pass (runs BEFORE all checks)

| Condition (all quantities VERIFIED) | Result |
|---|---|
| Quantity ≤ 10 g/ml (weight/measure units), `generic_name` VERIFIED, no tobacco keyword | **EXEMPT** — all checks NA (`NA_EXEMPT`), citation "Rule 26(a) exemption, quantity ≤10 g/ml verified" |
| Quantity ≤ 10 g/ml + tobacco keyword (gutkha, pan masala, zarda, khaini, snuff, tobacco, cigarette, bidi — case-insensitive, word-boundary, on generic_name raw) | **NEEDS_REVIEW** — "exemption uncertain: tobacco proviso" |
| Quantity ≤ 10 g/ml + `generic_name` not VERIFIED | **NEEDS_REVIEW** — "exemption uncertain: commodity type unverified" |
| Quantity > 25 kg/l | **NEEDS_REVIEW** — "Chapter II likely inapplicable; cement/fertilizer exception cannot be ruled out" (Rule 3(a)) |
| Pieces, no threshold crossed, or quantity not VERIFIED | No exemption — checks run normally |

Boundary note: the 10–20 g/ml proviso was withdrawn wef 01.07.2012 — ≤10 is the clean boundary; 10.5 g gets no exemption. Institutional/industrial, DPCO, hotel food, agricultural >50 kg, thread coils, loose garments are not detectable from a label — covered by the report footer, not the engine.

### 0.9 Interpretation registry (the four documented calls)

| # | Call | Where |
|---|---|---|
| 1 | contactable = phone OR email | R6 |
| 2 | ≥1000 g/ml expressed in grams/ml → PASS | R3 — flagged weakest, benchmark watch-list |
| 3 | MRP shorthand + taxes clause → NEEDS_REVIEW, not FAIL | R5 |
| 4 | street-level detail missing → NEEDS_REVIEW, not FAIL | R1 |
| 5 | predominantly = > 50 % of script-bearing characters, per declaration | R7 |
| 6 | embossed/relief numerals judged under the molded column (Rule 7 Table-I, 2018 substitution) | R8 |
| 7 | exactly-boundary PDP area → the less strict class (PDF path; the σ interval handles photos) | R8 |

**Pattern across all seven: where the law is ambiguous, we say NEEDS_REVIEW, never a wrong FAIL.**

---

## R1 — Manufacturer/packer/importer name + complete address

**Citation:** Rules 6(1)(a), 10(1) — LMPC (PC) Rules, 2011.
**Inputs:** `manufacturer_name`, `manufacturer_address` (unanchored fields — verified by gates G1–G4 + G6, tagged "unanchored-verified").
**Method:** two defenses — (A) deterministic patterns on the verified raw; (B) region analysis: OCR words inside the claimed box plus a dilation margin (guards against partial claims by the LLM). All patterns run on claim ∪ region text.

**Presence (locked):** `manufacturer_name` `ABSENT` → **FAIL** ("manufacturer name not found on label"); `UNREADABLE` → NA.

| Address state | Verdict |
|---|---|
| `ABSENT` | **FAIL** (missing) |
| Present, but no PIN AND no city/state pattern | **FAIL** — "not locatable" |
| PIN or city/state present, no street-level detail | **NEEDS_REVIEW** — INTERPRETATION #4 |
| PIN or city/state + street-level detail | **PASS** |

**Edge cases:** PIN = a standalone 6-digit word in the word index, outside the consumer-care box (never a substring). State list = enumerable config. A partial claim (LLM quoted half the address) is caught by defense B's dilation margin.
**Examples:** "Plot No. 12, MIDC, Nagpur, Maharashtra - 440010" → PASS · "Nagpur, Maharashtra" (no street) → NEEDS_REVIEW · "Made in India" only → FAIL "not locatable" · name missing with a complete address → FAIL (name).
**Fix:** print the full postal address — street, city, state or PIN.

## R2 — Common/generic name of commodity

**Citation:** Rule 6(1)(b).
**Inputs:** `generic_name`.

| Status | Verdict |
|---|---|
| `VERIFIED` non-empty | **PASS** |
| `ABSENT` | **FAIL** |
| `UNREADABLE` | **NA** |

**Edge cases / scope note:** this check certifies PRESENCE, and says so — semantic correctness of the name is out of scope.
**Example:** "Aloo Bhujia (Savoury Snack)" → PASS.
**Fix:** print the commodity's common/generic name.

## R3 — Net quantity in correct unit

**Citation:** Rules 6(1)(c), 13. **Dependency:** `net_quantity`.

| Verified quantity | Verdict |
|---|---|
| Unit outside {g, kg, ml, l, pcs}, or "dozen/score/gross" | **FAIL** — Rule 13(4) explicit |
| Value < 1 with unit kg/l ("0.5 kg") | **FAIL** — <1 kg must be grams, <1 L must be ml |
| ≥ 1000 expressed in g or ml ("1500 g") | **PASS** — INTERPRETATION #2, weakest call, benchmark watch-list |
| Normal ("200 g", "1.5 kg", "500 ml") | **PASS** |

**Edge case:** "1500 g" stays PASS — watch-listed, not failed (the unit is legal; the style is unusual).
**Examples:** "Net Wt. 200 g" → PASS · "0.5 kg" → FAIL · "1 dozen" → FAIL.
**Fix:** express as whole grams below 1 kg / whole ml below 1 L; allowed units g, kg, ml, l, pcs.

## R4 — Month & year of manufacture

**Citation:** Rule 6(1)(d). **Dependency:** `mfg_date`.

| Verified mfg_date | Verdict |
|---|---|
| Format-whitelisted (MM/YYYY, MON/YYYY, full month names; MFG/MANUFACTURED prefixes tolerated) | **PASS** |
| Unparseable | **FAIL** — valid formats required |
| Parseable but year < 2000 or > current year + 1, or a future date | **NEEDS_REVIEW** |

**Edge case:** this is a presence/format check, not a fact-check — plausibility issues are flagged, never failed.
**Examples:** "MFG 08/2026" → PASS · "August 2026" → PASS · "08/26" alone → FAIL.
**Fix:** print as MM/YYYY or Month YYYY (e.g. "MFG 08/2026").

## R5 — MRP prescribed wording (the most common violation)

**Citation:** Rules 2(m), 6(1)(e). **Dependency:** `mrp`.

| Verified MRP raw | Verdict |
|---|---|
| Full wording ("Maximum / Max. Retail Price") + price + "inclusive of all taxes" | **PASS** |
| Price present, taxes clause missing ("MRP Rs. 20") | **FAIL** — the taxes clause is unambiguous in law |
| "MRP" shorthand + taxes clause present | **NEEDS_REVIEW** — INTERPRETATION #3 |
| Multiple distinct MRP values on the label | **NEEDS_REVIEW** — "multiple MRP instances — possible revised-price sticker (Rule 6(3) makes reduced-MRP stickers legal)" |
| `ABSENT` | **FAIL** — "not found on label" |

**Edge cases:** taxes-clause matching is case- and punctuation-insensitive against a config variant list.

**Multiple-instance detection:** word-index anchor sweep (all MRP anchors); ≥ 2 distinct parsed values → the NEEDS_REVIEW row. Repeated identical values are not multiple.
**Examples:** "Maximum Retail Price Rs. 20 (inclusive of all taxes)" → PASS · "MRP Rs. 20" → FAIL · "MRP Rs. 20 (incl. of all taxes)" → NEEDS_REVIEW.
**Fix:** print as: Maximum Retail Price Rs. X (inclusive of all taxes).

## R6 — Consumer care details

**Citation:** Rule 6(2). **Inputs:** `consumer_care`.

| Status / content | Verdict |
|---|---|
| `VERIFIED`, parsed phone OR email present | **PASS** |
| `VERIFIED`, neither phone nor email | **FAIL** — "no contactable channel" (INTERPRETATION #1) |
| `ABSENT` | **FAIL** |
| `UNREADABLE` | **NA** |

**Example:** "Consumer Care: 1800-XXX-XXXX, care@haldirams.com" → PASS.
**Fix:** print a consumer-care phone number or email address.

## R7 — Declarations in Hindi (Devanagari) or English

**Citation:** Rule 9(4). **Inputs:** all `VERIFIED` raws + the word index.

| Situation | Verdict |
|---|---|
| Mandatory declarations predominantly Devanagari (U+0900–097F) or Latin | **PASS** |
| Predominantly neither script | **FAIL** |
| Claimed script vs word-index script composition disagree | **NEEDS_REVIEW** |
| Hindi-only label, effectively unverified (UNSUPPORTED_LANGUAGE) | **NEEDS_REVIEW** |

**Edge case:** digits and punctuation are script-neutral and never decide the verdict.

**Threshold (INTERPRETATION #5):** predominantly = > 50 % of script-bearing characters (digits, punctuation, whitespace excluded), per mandatory declaration.

## R8 — Minimum numeral height (MRP/quantity numerals)

**Citation:** Rule 7(2) + Table-I as substituted by GSR 629(E), w.e.f. 1.1.2018 (decision log 2026-09-18). **Dependency:** calibration — the class is keyed on the measured PDP area, not `net_quantity` (the quantity box is still needed to locate its numerals).

**Required minimums (Rule 7 Table-I, PDP-area classes — the 2018 substitution; the pre-2018 weight/volume table is superseded law):**

| PDP area (A, cm²) | Required numeral height |
|---|---|
| A < 50 | ≥ 1.0 mm normal · ≥ 1.5 mm molded |
| 50 < A < 100 | ≥ 1.5 mm · ≥ 3.0 mm molded |
| 100 < A < 500 | ≥ 2.5 mm · ≥ 4.0 mm molded |
| 500 < A < 2500 | ≥ 4.0 mm · ≥ 6.0 mm molded |
| 2500 < A | ≥ 6.0 mm · ≥ 6.0 mm molded |

**Input tiers (the calibration table):**

| Input | R8 result |
|---|---|
| Vector PDF | exact mm — pdfplumber char bbox, 1 pt = 0.3528 mm, ε = 0 |
| Photo, calibrated (`label_width_mm` supplied) | measured mm with a 3σ confidence band |
| Photo, uncalibrated | **NA** — `NO_SCALE_REFERENCE` |

**The 3σ decision rule (calibrated photos):** H = measured height, R = required mm, σ ≈ 0.05 × H (error budget: σ_px 4% + σ_scale 3% → 5% total):

- H + 3σ < R → **FAIL** (confident violation)
- H − 3σ ≥ R → **PASS**
- otherwise → **NEEDS_REVIEW** — the boundary zone never produces a verdict

**Class-interval rule (area uncertainty):** σ_A/A ≈ 7%; if A's 3σ interval straddles a class boundary → FAIL only if H + 3σ < R_min, PASS only if H − 3σ ≥ R_max (least / strictest candidate class), else NEEDS_REVIEW. Exact-boundary A on PDFs → less strict class (INTERPRETATION #7). Embossed/relief numerals → molded column (INTERPRETATION #6).

**Calibration pipeline (each stage can return NA, never a wrong scale):** Otsu segmentation → minAreaRect width → rectangularity gate ≥ 0.80 (shadows → NA with guidance) → tilt measurement (≤ ~15° absorbed, extreme → NA) → implausibility sanity check (median body-text height must lie within 0.5–4.0 mm) → scale = pixel width / label_width_mm → PDP area A = width × height in cm² (Rule 7(4)(a)).

**Edge cases:** a failed dependency (net_quantity not VERIFIED — the quantity numeral cannot be located) → NA `DEPENDENCY_UNAVAILABLE`; resolution floor ≥ 20 px/mm (below it, bands widen — more NEEDS_REVIEW, never a wrong verdict). Watch note: some compilations print 2.0 mm for the A < 50 molded row where the amendment gazette says 1.5 mm — we codify 1.5 (thresholds.config value).
**Examples (class 50 < A < 100, R = 1.5 mm, σ = 0.05 × H):** H = 1.0 → FAIL · H = 2.0 → PASS · H = 1.5 → NEEDS_REVIEW.
**Fix:** increase MRP/quantity numeral height to at least the required mm for this PDP area class.

## R9 — Clear space around the quantity declaration

**Citation:** Rule 8. **Scale-free — runs on every photo and every PDF.**

**The exclusion zone:** around the quantity-declaration box — 1× median digit height (h) above and below, 2×h left and right.

| Situation | Verdict |
|---|---|
| No other OCR word and non-text ink below threshold inside the zone | **PASS** |
| Any OCR word other than the declaration's own intersecting the zone | **FAIL** — "printed information too close" |
| Non-text ink density above a fixture-calibrated threshold inside the zone | **FAIL** — graphics and logos are "printed information" too |

**Edge case:** the word index alone misses graphics — that is why the ink-coverage check (b) exists; both must pass. PDF path: the zone is tested against pdfplumber objects (words, rects, lines, curves, images) — any non-quantity object's bbox intersecting the zone → the same FAIL (exact, ε = 0).

## R10 — Contrast of MRP/quantity numerals

**Citation:** Rule 9(1)(b). **Scale-free — runs on every photo and every PDF.**

**Method:** foreground = digit connected-component pixels (known exactly); background = declaration box minus digit pixels; WCAG relative luminance ratio C = (L_light + 0.05)/(L_dark + 0.05).

| Contrast | Verdict |
|---|---|
| C > 3.5 | **PASS** |
| 2.5 ≤ C ≤ 3.5 | **NEEDS_REVIEW** — the borderline band |
| C < 2.5 | **FAIL** — "does not contrast conspicuously" |
| Embossed / blown / moulded text (Rule 9 proviso: glass/plastic) | **NA** |

**Reference values (computed):** black-on-white 21:1 · red-on-white 6.7:1 · grey-160-on-white 2.6:1 (band) · yellow-on-white 1.1:1 (the classic violation).
**Honest flag:** the law says "contrasts conspicuously" with no legal number — the 3:1 threshold is our codified interpretation (WCAG large-text), reported as interpretive and fixture-calibrated.
**PDF path:** exact declared colours.

**Embossed/molded detector (serves R8's column choice + this proviso):** ΔE = CIE76 colour distance (digit pixels vs local background ring) + C above. ΔE < 10 AND C < 2.5 → same-ink relief → R10 NA + R8 molded column; ΔE ≥ 15 AND C < 2.5 → pale different-ink print → R10 FAIL + normal column; 10 ≤ ΔE < 15 or C in 2.5–3.5 → NEEDS_REVIEW. Thresholds in config, fixture-calibrated.

## R11 — No misleading quantity qualifiers

**Citation:** Rule 12(6). **Dependency:** `net_quantity` (its raw text).

| Quantity-declaration raw text | Verdict |
|---|---|
| No qualifier word | **PASS** |
| Contains a hard-list qualifier: {minimum, not less than, average, about, approximately} | **FAIL** — Rule 12(6) explicit |
| Contains "when packed" AND the commodity matches the Third Schedule list (26 items, config) | allowed (Rule 11(4)) — overall PASS if no hard-list word |
| Contains "when packed", no Third Schedule match | **NEEDS_REVIEW** |

**Edge case (the scoping rule):** the check runs on the quantity declaration's raw text ONLY, never the whole label — a brand called "All About Nuts" must never trigger it.
**Example:** "Net Wt. minimum 200 g" → FAIL.
**Fix:** print the exact net quantity without qualifiers ("Net Wt. 200 g").

---

## Appendix A — Reason codes

| Code | Meaning | Typical trigger |
|---|---|---|
| `NOT_PRINTED` | declaration not printed on the label | absent, non-mandatory NA context |
| `UNREADABLE_IMAGE` | image too poor to judge | readability R false |
| `VERIFY_FAILED` | claimed but unconfirmed | crop-verify / anchor gate failed |
| `LOW_CONFIDENCE` | verified but weak read | all gates pass, confidence < 0.60 |
| `UNSUPPORTED_LANGUAGE` | script beyond OCR quality | Devanagari-only field |
| `NO_SCALE_REFERENCE` | no calibration on a photo | R8 without label_width_mm |
| `DEPENDENCY_UNAVAILABLE` | a required field was not VERIFIED | e.g. R3/R8 without net_quantity |
| `NA_EXEMPT` | exemption layer removed the check | Rule 26(a) exempt package |
| `EXTRACTION_MISS` | no claim but a field-type anchor exists on the label | LLM did not extract a field whose keyword is printed |

Every code maps to a human-readable message + suggested action in config — never hardcoded.

## Appendix B — Where every number in this document comes from

Field-status table, decision tables R1–R7/R11: ENGINEERING.md F3 §3.2–3.3. R8–R10: ENGINEERING.md F2 §2.2–2.5. Exemption table: F4 §4.5. Reason codes: F1 §1.6 + F3 §3.2 (DEPENDENCY_UNAVAILABLE) + F4 §4.7 (NA_EXEMPT). Citations and the 11-check list: DECISIONS.md §3. Enums and result/fix shapes: CONTRACTS.md §2/§4.
