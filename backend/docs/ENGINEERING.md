# ENGINEERING.md — Proven Designs & Implementation Direction (BACKEND ONLY)

**Purpose:** every backend feature's approach, proven before it is coded. Per the proof-first rule (DECISIONS.md §8): math before code; agents translate these designs, they never make design decisions. Implementation correctness is enforced separately by fixtures/TDD.

**Scope:** backend build document. Frontend track builds against `CONTRACTS.md` only and never reads this file.

**Feature index:**

| # | Feature | Status |
|---|---|---|
| 1 | Extraction verification gauntlet | PROVEN — approved 2026-09-16 |
| 2 | Geometry engine (R8–R10) | PROVEN — approved 2026-09-17 |
| 3 | Rule engine framework + checks R1–R7, R11 | PROVEN — approved 2026-09-17 |
| 4 | Exemption layer + NA semantics | PROVEN — approved 2026-09-17 |
| 5 | Ingestion path (presign + S3 event) | PROVEN — approved 2026-09-17 |
| 6 | Report generator (annotation, PDF/CSV) | PROVEN — approved 2026-09-17 |
| 7 | API + storage (history/search/stats) | PROVEN — approved 2026-09-17 |
| 8 | Benchmark harness (accuracy/coverage methodology) | PROVEN — approved 2026-09-17 |

---

## Feature 1 — Extraction Verification Gauntlet

### 1.1 Goal

Whatever the LLM claims (wrong, hallucinated, misattributed) the system must never emit a wrong PASS/FAIL. The only permitted imperfection is "not determined" (NA), which must always carry a human-understandable reason and a suggested next action. A missing declaration on a readable label must be reported as a FAIL (violation), not silently swallowed as NA.

### 1.2 Error taxonomy — how the LLM can be wrong

| ID | Failure | Example |
|---|---|---|
| (a) | Hallucination — claims text that is not on the label | invents an address |
| (b) | Misread — real text, wrong characters | "Rs. 23" read as "Rs. 25" |
| (c) | Wrong box — right text, wrong location | box points at the brand logo |
| (d) | Miss — field exists, not found | (acceptable → NA / "absent" verdict) |
| (e) | Wrong attribution — a different field's text claimed as this one | "Best Before 20" reported as MRP |

(a), (b), (c), (e) must be caught. (d) is honest coverage loss.

### 1.3 Candidate approaches considered

| Approach | Verdict | Reason |
|---|---|---|
| A1 — LLM output + format validators only | REJECTED | Correctness = f(LLM quality): violates the core principle. A misread like "Rs. 25" passes every format check. |
| A2 — dual-LLM cross-check (two models must agree) | REJECTED | Two statistical models have correlated errors; not deterministic; 2x cost; "both agree" still proves nothing. |
| A3 — deterministic OCR-verified gauntlet with keyword anchors | **SELECTED** | Verification is independent of the LLM and deterministic: correctness bound depends only on the verifier. |

Documented upgrade path (NOT in MVP): Amazon Textract would strengthen verification further, but it is a 5th AWS service — team decision required per DECISIONS.md §5 before ever adopting it.

### 1.4 The chosen design — the gauntlet

One full-image pass of a classical OCR engine (Tesseract, packaged as a Lambda layer — deterministic: same image + version = same output, every run) produces a **word index**: `{word, box, confidence}` for the whole label. Every LLM claim then runs through six gates:

| Gate | Check | Catches |
|---|---|---|
| G1 | Box sanity — inside image bounds, non-degenerate | broken geometry |
| G2 | Raw text non-empty | empty claims |
| G3 | Parsed↔raw consistency — digits of `parsed` must appear in `raw`; unit token present | parse/claim mismatch |
| G4 | Crop-verify — normalized OCR text inside the claimed box must match the claimed raw (normalized, edit distance = 0) | (a) hallucination, (b) misread, (c) wrong box |
| G5 | Anchor check — the claimed box must contain an OCR-detected keyword anchor of the right field type | (e) wrong attribution |
| G6 | Self-reported confidence ≥ 0.60 (secondary signal only — never primary) | weak reads |

**Anchored vs unanchored fields.** `mrp`, `net_quantity`, `mfg_date`, `consumer_care` are anchored — their labels carry reliable keywords ("MRP", "Maximum Retail Price", "Net Wt", "MFG", "Manufactured", "Consumer Care"), so G5 applies. `manufacturer_name`, `manufacturer_address`, `generic_name` are unanchored (no guaranteed keyword) — G1–G4 + G6 apply and the report tags them "unanchored-verified". The asymmetry is principled: anchored fields drive numeric/wording verdicts (highest risk), unanchored fields drive presence verdicts.

**G4 normalization (locked — decision log 2026-09-17):** N(s) = casefold → Unicode NFKC → strip punctuation/symbols → collapse whitespace; numerals must match exactly in sequence; the gate is edit-distance-0 on N(raw) vs N(OCR text inside the claimed box). Same normalization family as the ε_ocr comparison (F8 §8.3) — one function, never two.

**Result mapping (deterministic switch, no logic to invent):**

| Condition | Result |
|---|---|
| G0 schema invalid (whole document unparseable) | scan = FAILED |
| raw = null | NA — reason: NOT_PRINTED or UNREADABLE_IMAGE (see 1.6) |
| G1–G5 any fail, raw non-null | NA — reason per failing gate |
| all pass, G6 fails | NEEDS_REVIEW — reason: LOW_CONFIDENCE |
| all pass | VERIFIED — feeds the rule engine |

### 1.5 Theorem — model-independent correctness

**Claim:** P(wrong PASS/FAIL verdict per field) ≤ ε_ocr, where ε_ocr is a property of the OCR verifier and normalization rules, not of the LLM.

**Proof (case analysis over §1.2):** a wrong verdict requires a false claim to pass every gate.

- (a) Hallucination: G4 requires the OCR to recognize the claimed string inside the box. OCR is recognition, not generation — it cannot output a specific string ("MRP Rs. 20") from blank/noise regions. P ≈ 0.
- (b) Misread: G4 passes only if the independent OCR errs in exactly the same way as the LLM. Different architectures (transformer LLM vs Tesseract's classical CV pipeline) ⇒ uncorrelated error modes; the normalized edit-distance-0 requirement removes near-miss agreement. P = ε_ocr, small, and independent of LLM quality.
- (c) Wrong box: the crop contains different text ⇒ G4 mismatch ⇒ NA. Sub-case: crop contains the same declaration printed elsewhere on the label — the claim is then true on the label and the verdict is still correct. Harmless.
- (e) Wrong attribution: G5 requires the field-type keyword anchor inside the claimed box. A "Best Before" box contains no MRP anchor ⇒ NA. G5 passing means an MRP keyword genuinely sits in that region.
- G3 blocks parsed/raw divergence deterministically.

**Corollary (the coverage/correctness split):** LLM quality only enters P(verified) = P(LLM reads correctly) × P(gates pass | LLM correct). The second term ≈ OCR crop sensitivity (high on clean printed crops). So a weaker LLM lowers coverage, never correctness — which is the core principle (DECISIONS.md §4). **PDF labels:** the text layer supplies the word index exactly (pdfplumber), no OCR involved ⇒ ε_ocr ≈ 0 in practice.

**Measuring ε_ocr (honesty clause):** the bound is verified empirically on fixtures: count events where (LLM wrong AND gates passed). Expected: 0. The benchmark reports this number (Feature 8).

### 1.6 Graceful degradation — absent vs unreadable, reasons, partial reports

**Readability score (deterministic):** R = (OCR word count ≥ 15) AND (mean OCR word confidence ≥ 0.65). Thresholds live in config, tuned on fixtures. R is computed once per image from the word index.

**The missing-vs-unreadable decision table:**

| Situation | Verdict | Meaning |
|---|---|---|
| R true, field null everywhere (LLM + no anchor anywhere in word index) | **confidently absent** → for a mandatory declaration this is **FAIL**: "declaration not found on label" | real violation, caught |
| R false (image too poor to judge) | NA — reason UNREADABLE_IMAGE | honest "cannot determine" |
| claim present, G4 fail | NA — reason VERIFY_FAILED | claimed but unconfirmed |
| all gates pass, G6 fail | NEEDS_REVIEW — reason LOW_CONFIDENCE | human glance |
| field text in Devanagari script (Tesseract hin quality insufficient) | NEEDS_REVIEW — reason UNSUPPORTED_LANGUAGE | correctness kept, coverage lost |
| no claim, R true, field-type anchor present in the word index | NEEDS_REVIEW — reason EXTRACTION_MISS | possible extraction miss — rescan suggested |

**Reason codes are first-class:** every NA/NEEDS_REVIEW carries one of `NOT_PRINTED`, `UNREADABLE_IMAGE`, `VERIFY_FAILED`, `LOW_CONFIDENCE`, `UNSUPPORTED_LANGUAGE`, `NO_SCALE_REFERENCE`, `DEPENDENCY_UNAVAILABLE`, `NA_EXEMPT`, `EXTRACTION_MISS` plus a human-readable message and a suggested action ("rescan in better lighting / flatter angle"), rendered in the report card. The mapping reason-code → message lives in a config file, not code.

**Partial report principle:** a failed gate on one field produces that field's NA — it never fails the scan. Only G0 (unparseable garbage) fails a scan. Every scan that parses produces a best-possible report: verified fields get full verdicts, the rest get honest reasons. The report always states "found X of 7 declarations".

### 1.7 Coverage model

Per-field coverage ≈ P(LLM extracts correctly) × P(crop verify passes | correct). Expected on clean printed English labels (to be measured, not assumed): ~85–95% per field. Hindi-only declarations: lower coverage (NEEDS_REVIEW), same correctness. These expectations are inputs to the demo narrative, not guarantees — fixtures and the benchmark replace them with measured numbers.

### 1.8 Cost & latency budget

| Step | Time | Cost |
|---|---|---|
| Tesseract full-image pass (one pass — serves G4, G5 and the readability score) | ~1–3 s | free (CPU in Lambda) |
| Bedrock Haiku extraction | ~2–5 s | <$0.01 per label |
| Gauntlet gates + rule engine | <0.1 s | free |
| **Total pipeline** | **< 10 s** | comfortably within Lambda 60 s timeout |

No additional AWS service is introduced; the 4-service lock (DECISIONS.md §5) holds.

### 1.9 Implementation direction (for the coding agent — translate, don't design)

1. **Word-index builder** — `build_word_index(image) -> [{word, box, confidence}]`: Tesseract via a Lambda layer (or pdfplumber for PDFs), pure function, own module.
2. **Gauntlet gates** — G1…G6 as six independent pure functions in separate files: input = (claim, word_index, image_meta) → pass/fail. No gate knows about the others.
3. **Anchor table** — `anchors.config`: field → list of keyword regexes. Code reads it; nothing is hardcoded. New patterns = config edit, no code change. Initial content (locked — decision log 2026-09-18): **mrp** → [MRP, M.R.P, M.R.P., Maximum Retail Price, Max. Retail Price]; **net_quantity** → [Net Wt, Net WT, Net Weight, Net Quantity, Net Contents, N.Wt]; **mfg_date** → [Mfg, MFG, Mfg., Manufactured, Manufactured by, Mfg Date, Date of Mfg] (Best Before / Exp deliberately excluded — different fields); **consumer_care** → [Consumer Care, Customer Care, Consumer Complaints, Customer Complaints, Toll Free, Toll-Free, Helpline]. Generic "Price" is excluded on purpose (G5 over-anchoring).
4. **Reason codes + messages** — `reasons.config`: code → {message, suggested_action}. The result mapper reads it.
5. **Readability score** — pure function over the word index; thresholds from config.
6. **Result mapper** — the decision tables of §1.4/§1.6 as one switch statement. No new logic.
7. **Extraction cache** — keyed by S3 object ETag; second scan of the same object skips Bedrock entirely. Backing store (locked — decision log 2026-09-17): S3 `cache/` prefix in the private uploads bucket, key = the object's ETag; the S3 trigger's `uploads/` prefix keeps cache writes from re-triggering the pipeline; IAM gains uploads-bucket write (infra-config update).

### 1.10 Acceptance criteria (all fixture-driven, deterministic — two runs must give identical output)

1. 10 hallucination fixtures → 10 NA (VERIFY_FAILED)
2. 10 misread fixtures → 10 NA (VERIFY_FAILED)
3. 10 wrong-attribution fixtures → 10 NA (no anchor in box)
4. 10 readable-label fixtures with a genuinely missing declaration → 10 FAIL "not found on label"
5. 10 poor-quality images (R false) → 0 false FAILs; NAs with UNREADABLE_IMAGE + suggested action
6. 20 clean labels → ≥ 90% of anchored fields VERIFIED (coverage bar)
7. Every NA/NEEDS_REVIEW in every fixture carries a reason code and a non-empty message

---

## Feature 2 — Geometry Engine (R8–R10)

### 2.1 Goal

Measure and judge the three physical requirements — numeral height (R8), clear space around the quantity declaration (R9), contrast of MRP/quantity numerals (R10) — deterministically, with confidence bands that make a wrong verdict impossible by construction.

### 2.2 The scale discovery (why the design looks like this)

- **R9 is scale-free by the law's own design:** clear space must be ≥ 1× numeral height above/below and ≥ 2× left/right. Both quantities are measured in the same pixels — scale cancels. R9 runs on every photo.
- **R10 is scale-free:** a colour ratio, no physical size involved. Runs on every photo.
- **R8 needs calibration:** Rule 7 Tables are in absolute millimetres. Absolute mm cannot be recovered from an uncalibrated photo — a physical impossibility, not an algorithmic gap — and the law defines no ratio alternative. Photo R8 therefore requires a scale reference; uncalibrated → NA (reason `NO_SCALE_REFERENCE`).

### 2.3 Photo-path product scope — the planar assumption

The geometry math assumes the photographed front face lies in one plane (every text region shares one scale). True for flat rectangular packets and cartons; false for bottles/jars (text wraps a curve). **Photo path supports flat packets + cartons only; curved surfaces are roadmap.** The PDF/artwork path has no such limit — artwork is flat by definition.

### 2.4 The chosen design — tiered calibration

| Input | R8 | R9 | R10 |
|---|---|---|---|
| Vector PDF | exact mm (pdfplumber char bbox; 1 pt = 0.3528 mm; ε = 0) | exact from text layer | exact from declared colours |
| Photo, calibrated | measured mm with 3σ confidence band | yes | yes |
| Photo, uncalibrated | NA — `NO_SCALE_REFERENCE` | yes | yes |

**User gives at most two things:** one instruction — plain background — and one optional number — `label_width_mm` (the width of what fills the frame; manufacturers know it from their artwork spec). Everything else is measured internally, never instructed.

**Calibration pipeline (photos), every stage can return NA — never a wrong scale:**
1. Otsu threshold + largest connected component → the packet blob (PIL + numpy + scipy.ndimage; no OpenCV)
2. `minAreaRect` → rotation-proof width in pixels (axis-aligned bbox would be wrong for rotated packets)
3. **Rectangularity gate:** blob area / (minAreaRect w×h) ≥ 0.80 — shadows merge with the packet and destroy rectangularity; below the gate → NA with shadow guidance (this prevents shadow-induced false FAILs)
4. **Tilt by measurement, not instruction:** trapezoid-ness = left vs right edge height ratio of the segmented blob. Tilt ≤ ~15° → error ≤ ~2%, absorbed by σ; larger → widen σ by the measured factor; extreme (> ~25%) → NA
5. **Implausibility sanity check:** implied median body-text height (word index, converted with the supplied scale) must lie within 0.5–4.0 mm; gross width mistakes (e.g. 2×, wrong object measured) push it outside → NA + "check the width you entered"
6. Scale s = pixel width / label_width_mm → all R8 measurements in mm + the PDP area A = (w_px/s) × (h_px/s) in cm² (rectangular package: one entire side — Rule 7(4)(a))

### 2.5 The math (verified by computation)

**Minimum resolution.** Digit-height measurement noise ≈ ±2 px (connected-component bbox jitter). Target σ_absolute ≤ 0.10 mm ⇒ 2 px ≈ 0.10 mm ⇒ **≥ 20 px/mm**. A 120 mm label must fill ≥ 2400 px of width — true for current phone cameras (3000–4032 px) when the label fills the frame; uploads must not be downscaled below this. Below it, σ grows, bands widen, more NEEDS_REVIEW — never a wrong verdict.

**Error budget.** σ_px ≈ 4% (2 px on a ~50 px digit); σ_scale ≈ 3% (user ruler ±2 mm on 100 mm + edge detection). σ_total = √(4² + 3²) = **5%**. On a 2 mm numeral: σ = 0.10 mm, band ±0.30 mm.

**3σ decision rule (the wrong-verdict impossibility mechanism):** with H = measured height, R = required mm:
- H + 3σ < R → **FAIL** (confident violation)
- H − 3σ ≥ R → **PASS**
- otherwise → **NEEDS_REVIEW** (the boundary zone never produces a verdict)

**Required mm — Rule 7 Table-I, AREA-BASED (as substituted by GSR 629(E), 23.6.2017, w.e.f. 1.1.2018; decision log 2026-09-18).** The class is keyed on the **principal-display-panel area A**, never on net quantity — the pre-2018 weight/volume table is superseded law:

| PDP area (A, cm²) | Normal | Blown / formed / molded on container |
|---|---|---|
| A < 50 | 1.0 mm | 1.5 mm |
| 50 < A < 100 | 1.5 mm | 3.0 mm |
| 100 < A < 500 | 2.5 mm | 4.0 mm |
| 500 < A < 2500 | 4.0 mm | 6.0 mm |
| 2500 < A | 6.0 mm | 6.0 mm |

A comes from the same calibration (§2.4 step 6) or exact page dimensions on PDFs. **Class-interval rule (area uncertainty folded into the 3σ rule):** σ_A/A ≈ √(5%² + 5%²) ≈ 7%; if A's 3σ interval straddles a class boundary, take R_min = the least strict and R_max = the strictest candidate required mm — **FAIL only if H + 3σ < R_min; PASS only if H − 3σ ≥ R_max; otherwise NEEDS_REVIEW.** With A well inside a class (the common case) R_min = R_max and the plain rule applies; a wrong verdict is impossible in either direction. PDFs: σ_A = 0 → exact class; an exactly-boundary A uses the less strict class (INTERPRETATION #7 — the gazette's open intervals leave it undefined; never-wrong-FAIL decides). Embossed/relief numerals use the molded column (INTERPRETATION #6 — the 2018 heading drops "embossed"; read as formed/molded on the container). **Watch note:** some compilations print 2.0 mm for the A < 50 molded row where the amendment gazette says 1.5 mm — we codify 1.5 (official text); it is a thresholds.config value. **Scope note:** the substituted 7(2) governs "any numeral and letter"; the MVP scope stays MRP + quantity numerals (locked) — declaration letters and the 7(3) width proviso (width ≥ ⅓ height) are roadmap.

Verified examples (class 50 < A < 100, R = 1.5 mm, σ = 0.05 × H): H = 1.0 → FAIL; H = 2.0 → PASS; H ≈ 1.5 → NEEDS_REVIEW. Under approximately normal errors, P(false verdict) ≈ 0.13% — and 0 in the boundary zone, because no verdict is issued there.

**Width-input error analysis ("zara aage piche" case).** A wrong width is a uniform, one-directional scale error: it scales all R8 measurements equally and cannot touch R9/R10 at all.
- ±2–10% (normal measurement sloppiness): absorbed — same verdict, or NEEDS_REVIEW at the boundary. Verified: ±2% never changes a verdict; a true 1.5 mm violation still FAILs correctly even with +20% width error.
- ~15–20%: mostly still correct or inconclusive (the band is 15% wide). A wrong verdict needs >15% width error AND a genuinely borderline label (within 15% of the legal minimum) AND matching direction — all three together are rare.
- Gross mistakes (≥ 2×, wrong object measured): caught by the §2.4 sanity check → NA.

**R9 (scale-free).** h = median digit height (connected components). Exclusion zone around the quantity-declaration box: 1×h above/below, 2×h left/right. Two checks: (a) word-index — any OCR word other than the declaration's own intersecting the zone → FAIL "printed information too close"; (b) ink coverage — non-text ink density in the zone above a fixture-calibrated threshold → same FAIL (graphics and logos are "printed information" too; the word index alone misses them). Rectangle intersection is exact; the only error source is box detection, measured on fixtures. PDF path: the zone is tested against pdfplumber objects — any non-quantity word, rect, line, curve or image whose bbox intersects the zone → the same FAIL (exact, ε = 0, no pixel thresholding).

**R10 (scale-free).** Foreground = digit connected-component pixels (known exactly — no thresholding guess); background = the declaration box minus digit pixels. Contrast = WCAG relative luminance ratio C = (L_light + 0.05)/(L_dark + 0.05), L = 0.2126R′ + 0.7152G′ + 0.0722B′. Computed reference values: black-on-white 21:1, red-on-white 6.7:1, grey-160-on-white 2.6:1, yellow-on-white 1.1:1 (the classic violation). **Initial threshold 3:1 — honest flag:** the law says "contrasts conspicuously" with no legal number; 3:1 is our codified interpretation (WCAG large-text), reported as interpretive and calibrated on fixtures. Borderline 2.5–3.5 → NEEDS_REVIEW. Embossed/blown/moulded text (Rule 9 proviso: no contrast required on glass/plastic) → NA. PDF path: exact declared colours.

**Embossed/molded detector (empirical, fixture-calibrated — decision log 2026-09-18; serves R8's column choice and R10's proviso):** digit pixels vs local background ring (box dilated by 2× digit height, other text excluded): ΔE = CIE76 distance (RGB → Lab, D65, pure numpy) and C = the WCAG ratio above. **ΔE < 10 AND C < 2.5** → same-ink relief (shading, no pigment) → molded column + R10 NA; **ΔE ≥ 15 AND C < 2.5** → different-ink pale print → normal column + R10 FAIL (the real violation); ambiguous band (10 ≤ ΔE < 15, or C in 2.5–3.5) → NEEDS_REVIEW. Thresholds in thresholds.config, calibrated on the embossed + pale-print fixtures (§2.8 items 7–8). PDF path: exact — text colour vs background colour from the declared colours.

### 2.6 Rejected alternatives

| Alternative | Verdict | Reason |
|---|---|---|
| Coin in frame (₹10, Hough circle) for scale | REJECTED | zero user measurement, but adds a second CV detection problem to the most delicate feature; one designed path beats two |
| Full guided capture (plain bg + fill frame + straight-on) | REJECTED | three instructions users won't follow; two of the three are measurable internally instead |
| Photo R8 = always NA (PDF-only R8) | KEPT AS PRE-AGREED SHRINK | the automatic fallback if the calibration path proves flaky during the build — all other checks unaffected |
| OpenCV in Lambda | REJECTED | ~100 MB layer, slow deploys; PIL + numpy + scipy.ndimage cover every primitive needed |

### 2.7 Implementation direction (translate, don't design)

1. `measure_numeral_height(image, box)` → median digit height in px (connected components on the binarized crop)
2. `calibrate_photo(image, label_width_mm)` → scale + σ, or a NA reason — segmentation, minAreaRect, rectangularity, tilt and sanity are sequential stages, each able to return NA. **minAreaRect (pure numpy, no OpenCV — decision log 2026-09-18):** PCA on the binary blob's pixel coordinates — the 2×2 covariance eigenvectors (np.linalg.eigh, closed form) give the rectangle's axes exactly for a filled rectangle; extents along each axis = rotation-proof width/height. Rounded-corner overestimate stays inside the 0.80 rectangularity gate's margin and is absorbed by the 5% σ budget
3. `check_r8(height_mm, sigma, required_mm)` → 3σ band verdict; required mm from the Rule 7 Table I lookup (pack class from declared net quantity) — all thresholds in config
4. `check_r9(word_index, quantity_box, h_px, ink_map)` → exclusion-zone verdict
5. `check_r10(image, digit_pixels, box)` → contrast ratio + band verdict
6. `thresholds.config` — contrast threshold, band widths, rectangularity gate, sanity bounds, resolution floor, Rule 7 table
7. All pure functions; deterministic; two runs = identical output

### 2.8 Acceptance criteria (fixture-driven)

1. Synthetic 1.0 mm numeral image @ 25 px/mm with correct width (class 50 < A < 100, required 1.5 mm) → FAIL, measured value reported
2. Same at 2.0 mm → PASS
3. Boundary (1.4–1.6 mm) → NEEDS_REVIEW, never a verdict; a PDP area within 3σ of a class boundary → NEEDS_REVIEW (class-uncertainty row)
4. Photo without `label_width_mm` → R8 = NA (`NO_SCALE_REFERENCE`) while R9/R10 return full results
5. Shadowed photo (rectangularity < 0.80) → R8 = NA with shadow guidance
6. Width off by 2× → R8 = NA via sanity check, message asks to re-check width
7. Yellow-on-white quantity → R10 FAIL; grey-160-on-white → NEEDS_REVIEW band; black-on-white → PASS
8. Same-ink relief numeral (ΔE < 10, C < 2.5) → R10 = NA per proviso AND R8 uses the molded column; pale different-ink print (ΔE ≥ 15, C < 2.5) → R10 FAIL and R8 uses the normal column
9. Vector PDF label → all three checks exact (mm from character boxes)
10. Two runs of every fixture → identical output

---

## Feature 3 — Rule Engine Framework + Checks R1–R7, R11

### 3.1 Goal

Run the eight extraction-based checks deterministically, each producing a CONTRACTS rule-result item, with ambiguity resolved toward `NEEDS_REVIEW` — never a wrong FAIL. R8–R10 live in the geometry modules (Feature 2); this feature provides the framework they all run inside.

### 3.2 Framework design

**Field-status pre-resolution (the structural decision).** Checks never handle missing/unreadable logic themselves. The framework first resolves every field's status into a `field_status` map — the explicit interface Feature 1's gauntlet output feeds (closing the coupling gap):

| Status | Meaning |
|---|---|
| `VERIFIED` | passed all gates — raw text is on the label |
| `ABSENT` | null everywhere AND readability = true AND no field-type anchor anywhere in the word index → fail-able (the missing-vs-unreadable lock) |
| `UNREADABLE` | readability = false → NA territory |
| `NEEDS_REVIEW` | verification inconclusive or failed — claim present (LOW_CONFIDENCE, VERIFY_FAILED, UNSUPPORTED_LANGUAGE) or no claim with an anchor present (EXTRACTION_MISS) |
| `NA_EXEMPT` | exemption layer (Feature 4) removed this field from scope |

**Gauntlet → field-status bridge (locked — decision log 2026-09-17; the complete mapping, no gaps):**

| Gauntlet result (F1 §1.4/§1.6) | field_status |
|---|---|
| all gates pass | `VERIFIED` |
| G6 fail only (LOW_CONFIDENCE) | `NEEDS_REVIEW` |
| readability R false (UNREADABLE_IMAGE) | `UNREADABLE` |
| no claim, R true, no field-type anchor in the word index (NOT_PRINTED) | `ABSENT` |
| no claim, R true, field-type anchor present (EXTRACTION_MISS) | `NEEDS_REVIEW` |
| claim present, G1–G5 fail (VERIFY_FAILED / UNSUPPORTED_LANGUAGE) | `NEEDS_REVIEW` — dependent checks `NA` with `DEPENDENCY_UNAVAILABLE`, the field's own reason carried in evidence |
| exemption applied (Feature 4) | `NA_EXEMPT` (overrides all rows above) |

**Pure-function checks.** `check(context) → CheckResult`; `context = {extraction, word_index, field_status, readability, config}`. Checks are independent of each other — no ordering, no shared state, one file per check, fixture-testable in isolation.

**Dependency declaration.** Each check declares the fields it requires (e.g. R3 and R8 need `net_quantity`). A required field not in `VERIFIED`/`ABSENT` status → the check returns `NA` with reason `DEPENDENCY_UNAVAILABLE` — distinct from "field absent" (that's a FAIL case).

**Everything pattern-shaped lives in configs, not code:** MRP wording tiers, date formats, PIN regex, state list, qualifier words, Third Schedule list, fix messages. Pattern logic = code; pattern data = config.

### 3.3 Check specs (decision tables)

**R2 — generic name (presence only).** `VERIFIED` non-empty → PASS; `ABSENT` → FAIL (fix: print the commodity's common/generic name); `UNREADABLE` → NA. Semantic correctness of the name is out of scope — this check certifies presence, and says so.

**R3 — net quantity unit.** Dependency: `net_quantity`.

| Verified quantity | Verdict |
|---|---|
| Unit outside {g, kg, ml, l, pcs}, or "dozen/score/gross" | FAIL — Rule 13(4) explicit |
| Value < 1 with unit kg/l ("0.5 kg") | FAIL — <1 kg must be grams / <1 L must be ml |
| ≥ 1000 expressed in g or ml ("1500 g") | PASS — INTERPRETATION #2, weakest call, on the benchmark watch-list |
| Normal ("200 g", "1.5 kg", "500 ml") | PASS |

**R4 — mfg date.** Format whitelist (config): MM/YYYY, MON/YYYY, full month names; MFG/MANUFACTURED prefixes tolerated. Unparseable → FAIL (fix: valid formats). Parseable but year < 2000 or > current year + 1, or a future date → NEEDS_REVIEW (this is a presence/format check, not a fact-check — plausibility issues flagged, not failed).

**R5 — MRP wording (the most common violation; three tiers + sticker rule).**

| Verified MRP raw | Verdict |
|---|---|
| Full wording ("Maximum / Max. Retail Price") + price + "inclusive of all taxes" | PASS |
| Price present, taxes clause missing ("MRP Rs. 20") | **FAIL** — taxes clause is unambiguous in law |
| "MRP" shorthand + taxes clause present | NEEDS_REVIEW — INTERPRETATION #3 |
| Multiple distinct MRP values on the label | NEEDS_REVIEW — "multiple MRP instances — possible revised-price sticker (Rule 6(3) makes reduced-MRP stickers legal)" |
| `ABSENT` | FAIL — "not found on label" |

Taxes-clause matching is case- and punctuation-insensitive against a config variant list. Initial variants (locked — decision log 2026-09-18): (inclusive of all taxes), inclusive of all taxes, (Inclusive of All Taxes), (incl. of all taxes), including all taxes, MRP inclusive of all taxes.

**Multiple-instance detection (deterministic — decision log 2026-09-17):** sweep the whole word index for MRP anchor matches (anchors.config); parse the price tokens of each anchored region; **≥ 2 distinct values → the sticker-rule NEEDS_REVIEW row above**. Repeated identical values (e.g. printed front and back) are not multiple.

**R6 — consumer care.** `VERIFIED` → parsed phone or email present → PASS; neither → FAIL "no contactable channel" (INTERPRETATION #1); `ABSENT` → FAIL; `UNREADABLE` → NA.

**R7 — language.** Script composition (Unicode blocks, digits/punctuation neutral) of all `VERIFIED` raws + cross-check against word-index scripts. Any mandatory declaration predominantly (INTERPRETATION #5: > 50 % of script-bearing characters — digits, punctuation, whitespace excluded — per mandatory declaration) neither Devanagari (U+0900–097F) nor Latin → FAIL; the two sources disagree → NEEDS_REVIEW; label effectively unverified (Hindi-only, `UNSUPPORTED_LANGUAGE`) → NEEDS_REVIEW.

**R11 — misleading qualifiers.** Scope: the quantity declaration's raw text ONLY (never the whole label — "All About Nuts" brand name must not trigger). Hard list {minimum, not less than, average, about, approximately} → FAIL (Rule 12(6) explicit). "When packed": if the commodity matches the Third Schedule list (config, 26 items) → allowed (Rule 11(4)) → overall PASS if no hard-list words; no match → NEEDS_REVIEW.

**R1 — name + complete address (two defenses).** Defense A: deterministic patterns on the verified raw. Defense B: region analysis — OCR words inside the claimed box plus a dilation margin (guards against partial claims by the LLM).

**Presence (locked — decision log 2026-09-17):** `manufacturer_name` `ABSENT` → **FAIL** ("manufacturer name not found on label"); `UNREADABLE` → NA. The address table below governs the rest.

| Address state | Verdict |
|---|---|
| `ABSENT` | FAIL (missing) |
| Present, but no PIN AND no city/state pattern | FAIL — "not locatable" |
| PIN or city/state present, no street-level detail | NEEDS_REVIEW — INTERPRETATION #4 |
| PIN or city/state + street-level detail | PASS |

PIN = standalone 6-digit word in the word index, outside the consumer-care box. State list = enumerable config. All R1 patterns run on claim ∪ region text.

### 3.4 Interpretation registry (documented, judge-defensible)

| # | Call | Where |
|---|---|---|
| 1 | contactable = phone OR email (name/address nuance folded into contactability) | R6 |
| 2 | ≥1000 g/ml expressed in grams/ml → PASS | R3 — flagged weakest, benchmark watch-list |
| 3 | MRP shorthand + taxes clause → NEEDS_REVIEW, not FAIL | R5 |
| 4 | street-level detail missing → NEEDS_REVIEW, not FAIL | R1 |
| 5 | predominantly = > 50 % of script-bearing characters, per declaration | R7 |
| 6 | embossed/relief numerals judged under the molded column (Rule 7 Table-I, 2018 substitution) | R8 |
| 7 | exactly-boundary PDP area → the less strict class (PDF path; the σ interval handles photos) | R8 |

Pattern across all seven: **where the law is ambiguous, we say NEEDS_REVIEW, never a wrong FAIL.**

### 3.5 The conditional guarantee (honest statement)

Feature 1–2 guarantees were theorems. This feature's guarantee is conditional: **correct, GIVEN that the decision tables and pattern configs cover the format variety present in real labels.** The proof of coverage is empirical — the classification-rate acceptance bar below and the benchmark (Feature 8). Config coverage is a measured number, not an assumption.

### 3.6 False-verdict analysis (per check)

- **False FAIL paths:** interpretive ambiguity → all routed to NEEDS_REVIEW (registry above); partial address extraction → region analysis; sticker MRP → multiple-instance rule; R11 scoping → quantity raw only. Remaining false-FAIL risk: pattern configs miss a legitimate format → lands in FAIL tier wrongly — caught by the classification bar and benchmark, fixed by config edit (no code change).
- **False PASS paths:** only via unverified fields (coverage loss, bounded by Feature 1's analysis); a `VERIFIED` field + a passing pattern is a genuine pass by construction.
- **Theorem:** a FAIL is emitted only when (a) the field is confidently absent on a readable label, or (b) an explicit pattern matched on verified text. Both deterministic.

### 3.7 Implementation direction (translate, don't design)

1. `resolve_field_statuses(gauntlet_output, readability, exemptions)` → the `field_status` map (exemptions come from Feature 4's `evaluate_exemptions`, §4.5; if that feature is not yet built, default: nothing exempt)
2. `run_checks(context)` → iterates registered checks; each check = one module, one pure function, its own fixtures
3. Each check declares `requires` (field list); framework short-circuits missing dependencies to `NA` + `DEPENDENCY_UNAVAILABLE`
4. `patterns.config` — all tier lists, regexes, whitelists, Third Schedule items, fix messages per rule
5. No check reads the LLM's confidence directly; verdicts trace to `field_status` + patterns only

### 3.8 Acceptance criteria (fixture-driven)

1. Field-status resolution: 20 fixtures → statuses match hand-labelled expectations
2. **Classification-rate bar: on 20 clean fixtures, ≥ 85% of applicable checks return a definitive verdict (PASS/FAIL), not NEEDS_REVIEW** — the anti-flooding guarantee
3. Every decision-table row above has ≥ 1 fixture — especially all R5 tiers, the sticker case, all R3 rows, all R1 rows
4. R11 scoping: a label with "All About Nuts" branding and clean quantity → R11 PASS
5. Dependency: quantity-`UNREADABLE` fixture → R3 and R8 both `NA` with `DEPENDENCY_UNAVAILABLE`
6. Every FAIL carries its fix text; every NA/NEEDS_REVIEW carries a reason code + message
7. Two runs of every fixture → identical output

---

## Feature 4 — Exemption Layer + NA Semantics

### 4.1 Goal

Rule 26 (and Rule 3) exempt certain packages from LMPC declaration requirements. The system must apply these exemptions **without ever exempting a package that is not legally exempt** — a false exemption is a **false PASS**: it hides real violations, the exact opposite failure mode of Features 1–3 (which protect against false verdicts). This feature is small but the risk direction is inverted, so the bar for granting an exemption is deliberately strict.

### 4.2 The inverted-risk principle

Features 1–3: an uncertain field may degrade to NA/NEEDS_REVIEW (honest "we don't know") — never a wrong verdict. Feature 4 mirrors this: **an uncertain exemption may degrade to NEEDS_REVIEW — never a wrong exemption.** Exemption requires positive, verified evidence; absence of evidence is treated as "not exempt".

### 4.3 What the law says (verified against the gazette text)

| Provision | Text (source: WB gazette PDF of the 2011 Rules; amendments noted) | Consequence |
|---|---|---|
| Rule 26(a) | "the net weight or measure of the commodity is ten gram or ten milli litre or less, **if sold by weight or measure**" — nothing in the rules applies | ≤10 g/ml packs are fully exempt. Quantity in pieces is NOT covered (qualifier: "sold by weight or measure") |
| Rule 26(a) proviso (historical) | 10–20 g/ml packs still needed MRP + net quantity — **withdrawn wef 01.07.2012** (GSR 748(E) 24.10.2011) | No middle zone exists today: ≤10 g/ml is the clean boundary |
| Rule 26(a) proviso (current, amendment-era) | tobacco and tobacco products are carved out of the ≤10 g/ml exemption (per consolidated-rule summaries; not in base text) | A <10 g pack that is a tobacco product is NOT exempt |
| Rule 3(a) | Chapter II does not apply to packages >25 kg or 25 litre, **excluding cement and fertilizer sold in bags up to 50 kg** | Our checks R1–R11 are Chapter II checks; a genuine >25 kg pack needs none of them |
| Rule 3(b) | Chapter II does not apply to industrial/institutional consumer packages | Not detectable from a label — documented limitation |
| Rule 26(b)–(d) | hotel/restaurant fast food; DPCO scheduled formulations; agricultural farm produce above 50 kg | Not deterministically detectable — documented limitation |

### 4.4 Detectable vs not-detectable (this defines the MVP layer)

**Detectable (deterministic, from verified fields):**
1. Quantity ≤ 10 g/ml (weight/measure units) — Rule 26(a)
2. Quantity > 25 kg/l — Rule 3(a) (Chapter II inapplicability)

**Not detectable from a label photo (roadmap; report footer covers them):**
institutional/industrial consumer packages (Rule 3(b)), agricultural produce >50 kg (Rule 26(d)), DPCO scheduled formulations (Rule 26(c)), hotel/restaurant fast food (Rule 26(b)), thread sold in coils, loose garments (2022 amendment). Report footer states: "This tool assumes non-exempt retail packaged goods."

### 4.5 The decision table (the entire feature)

Run after gauntlet + before field-status resolution (feeds the `exemptions` argument of `resolve_field_statuses`, §3.7 item 1).

| Condition (all quantities VERIFIED) | Result | Citation |
|---|---|---|
| Quantity ≤10 g/ml (weight/measure units), `generic_name` VERIFIED, no tobacco keyword in generic_name raw | **EXEMPT** — all checks NA; all declarations `NA_EXEMPT` | Rule 26(a) |
| Quantity ≤10 g/ml, tobacco keyword matched (config list on generic_name raw) | **NEEDS_REVIEW** — "exemption uncertain: tobacco proviso" | Rule 26(a) proviso (amendment) |
| Quantity ≤10 g/ml, `generic_name` not VERIFIED (cannot rule out tobacco) | **NEEDS_REVIEW** — "exemption uncertain: commodity type unverified" | Rule 26(a) proviso (amendment) |
| Quantity >25 kg/l | **NEEDS_REVIEW** — "Chapter II likely inapplicable; cement/fertilizer exception cannot be ruled out" | Rule 3(a) |
| Quantity in pieces, or no threshold crossed, or quantity not VERIFIED | **No exemption** — checks run normally (each check's own dependency logic applies) | Rule 26(a) qualifier |

Tobacco keyword list is a config (`tobacco.config`): gutkha, pan masala, zarda, khaini, snuff, tobacco, cigarette, bidi — matched case-insensitively on the verified generic_name raw text.

### 4.6 False-exemption analysis (the theorem)

Enumerate every path to a wrong exemption:
- (a) quantity not VERIFIED → exemption branch never entered (gate on VERIFIED);
- (b) quantity misparsed (e.g. "5 g" read as "5 kg") → G3 (parsed↔raw consistency) rejects it before Feature 4 sees it;
- (c) tobacco product under 10 g → keyword gate or unverified-generic_name gate → NEEDS_REVIEW, never exempt;
- (d) >25 kg pack of cement/fertilizer (legally needs declarations) → NEEDS_REVIEW, never exempt;
- (e) DPCO/hotel/agricultural/institutional package scanned → treated as non-exempt → checks run; worst case is a false FAIL on a legally exempt package — visible, not hidden, and covered by the report footer.

**Theorem:** an EXEMPT verdict is emitted only when the quantity is VERIFIED, parsed in weight/measure units, ≤10 g/ml, and the commodity type is VERIFIED non-tobacco. Every input to that conjunction is deterministic. The only false-exemption path left is a G3-passing misread that turns a >10 g value into a ≤10 g value while preserving digit consistency — bounded by Feature 1's ε_ocr, and independent of the LLM.

### 4.7 NA_EXEMPT semantics (closing the loop from Feature 3)

- `field_status = NA_EXEMPT` for every declaration field; every check R1–R11 returns `NA` with reason code `NA_EXEMPT` (introduced with this feature and approved in its decision-log entry) and citation "Rule 26(a) exemption, quantity ≤10 g/ml verified"
- Summary reports exemptions as a separate count, never inside PASS — an exempt scan must not look like a compliant scan
- The two NEEDS_REVIEW rows surface as a single top-level `NEEDS_REVIEW` verdict with the reason string from the table above
- Frontend contract (additive change, CONTRACTS.md §2 field rules): scan record gains an optional `exemption` object `{ "applied": bool, "citation": "Rule 26(a)", "reason": "..." }`. Exempt scans end in `DONE` (status machine unchanged) with all results `NA` — the "Exempt under Rule 26(a)" banner reads `exemption.applied`; exemption-uncertain scans end in `NEEDS_REVIEW` with the table's reason string

### 4.8 Implementation direction (translate, don't design)

1. `evaluate_exemptions(gauntlet_output)` → pure function returning one of: `EXEMPT`, `NEEDS_REVIEW(reason)`, `NONE`; consumed by `resolve_field_statuses`
2. Order matters: run AFTER the gauntlet (needs VERIFIED statuses), BEFORE check execution
3. `tobacco.config` alongside `patterns.config`; keyword matching on raw text, case-insensitive, word-boundary
4. Unit conversion to a canonical g/ml basis before threshold comparison (reuse the R8/R9 unit table — never write a second one)
5. No LLM call anywhere in this feature; no geometry involved

### 4.9 Acceptance criteria (fixture-driven)

1. Fixture set: sachet ≤10 g (clean generic name) → EXEMPT, all checks NA
2. Sachet ≤10 g + gutkha keyword → NEEDS_REVIEW with tobacco reason
3. Sachet ≤10 g + generic_name ABSENT → NEEDS_REVIEW with unverified-commodity reason
4. 30 kg package → NEEDS_REVIEW with Rule 3 reason
5. "6 pcs" quantity → no exemption, checks run
6. 10.5 g / 11 g boundary fixtures → no exemption (threshold is ≤10, and the 10–20 g proviso is withdrawn)
7. Exempt scan summary: exemption counted separately from PASS
8. Two runs of every fixture → identical output

---

## Feature 5 — Ingestion Path (presign + S3 event)

### 5.1 Goal

Move a label photo/PDF from the browser into the processing pipeline **exactly once**, using only the locked architecture (DECISIONS.md §5): presigned direct upload to S3, ONE Lambda invoked two ways (Function URL for the API, S3 `ObjectCreated` trigger for processing), DynamoDB for state. Duplicate S3 events and Lambda retries must be provably unable to cause double processing, torn writes, or double cost.

### 5.2 The trap — why this feature has an idempotency theorem

S3 event notifications are delivered **at-least-once** (documented behavior; duplicates occur). Lambda asynchronous invocations retry on error. Consequences without a guard: two pipeline executions for one object — double Lambda compute, two concurrent Bedrock calls that both miss the ETag-keyed extraction cache (the race: neither has written it yet), and interleaved writes to the same scan record.

### 5.3 Candidate approaches considered

| Approach | Verdict | Reason |
|---|---|---|
| B1 — no guard, trust exactly-once delivery | REJECTED | at-least-once delivery is documented |
| B2 — event-ID dedup store (TTL'd event IDs) | REJECTED | keys the wrong dimension (the event, not the object); extra moving parts; ignores the state machine |
| B3 — DynamoDB conditional claim (atomic test-and-set on `status`) | **SELECTED** | state-based, zero new infrastructure, and the frozen state machine itself becomes the idempotency gate |
| B4 — queue between S3 and Lambda | REJECTED | violates the 4-service lock (no queues) |

### 5.4 The chosen design

**POST /upload** (Function URL invocation):

1. Validate `content_type` ∈ {`image/jpeg`, `image/png`, `application/pdf`} — else `400 BAD_REQUEST`. Validate `label_width_mm`: optional, number > 0 — else `400`.
2. Derive extension (.jpg / .png / .pdf) and `source_type` (`application/pdf` → `pdf`, else `photo`).
3. Generate `scan_id`: `SC-` + 6 chars from `[A-Z0-9]` minus `0/O/1/I` (CONTRACTS.md §2).
4. Write the PENDING record with `ConditionExpression: attribute_not_exists(scan_id)` (collision → regenerate, max 3 attempts). Shape: `scan_id, status=PENDING, created_at, updated_at, input{filename, content_type, source_type, label_width_mm, s3_key, size_bytes: null}, product: null, summary: null, results: null, error: null` — every key always exists, unknowns are `null` (CONTRACTS.md convention). `input.size_bytes` is filled later, from the S3 event (§ below) — at PENDING time the size is unknown, so it is `null`.
5. Presigned PUT: `generate_presigned_url("put_object", key="uploads/{scan_id}.{ext}", ContentType, Expires=900)`. ContentType is part of the signature — the client must send that exact header; tampering → S3 `403`.
6. Respond `200 {scan_id, upload_url, expires_in: 900}` — the frozen contract shape.

**Causality (liveness):** the PENDING record is written before the presigned URL exists; the object can only exist after the client received the URL. Therefore every event for `uploads/{scan_id}.*` arrives after its record exists — no record/event race is possible by construction.

**S3 ObjectCreated handler** (same Lambda, event invocation):

1. Trigger configured on `labelcheck-uploads` only, prefix `uploads/`, `s3:ObjectCreated:*` (multipart completions included — belt and braces; browsers PUT single-part).
2. **Size gate** (from the event's `s3.object.size` — free, no download): > 20 MB → conditional transition to `FAILED` (`OVERSIZED_FILE`, guard `status = :pending`), log, return.
3. **The claim — the single gate**: conditional `UpdateItem`:
   - `ConditionExpression: status = :pending`
   - `UpdateExpression: SET status = :processing, updated_at = :now, input.size_bytes = :size`
   - `ConditionalCheckFailedException` → duplicate / late event / unknown object → log + **return success** (never raise — an error response makes S3 retry, pure noise; idempotency is unaffected either way).
   - The condition is deliberately `status = :pending` and NOT `attribute_not_exists(status) OR ...`: the latter would create a phantom `PROCESSING` record for objects with no scan record (direct bucket PUT).
   - The handler derives `scan_id` by parsing the S3 key (`uploads/{scan_id}.{ext}`) — never from any other source.
4. Pipeline handoff to the Feature 1–4 modules, same invocation.
5. `try/finally`: exception → `FAILED` with `{code, message}` (codes include `EXTRACTION_FAILED` — Bedrock call failure; decision log 2026-09-17); success → terminal `DONE | NEEDS_REVIEW`: **NEEDS_REVIEW iff any result is NEEDS_REVIEW or the exemption layer is uncertain; otherwise `DONE`** (locked — decision log 2026-09-17). A normal failure never leaves a stuck record.

**Stale-state reconciliation (three guards, all conditional writes; functions defined here, invoked from the `GET /scans/{id}` route — Feature 7 wires the route):**

| Guard | Trigger | Action |
|---|---|---|
| `STALE_PROCESSING` reaper | `status = PROCESSING` and `updated_at` older than 5 min (5× the worst case: pipeline < 10 s, Lambda hard cap 60 s) | conditional → `FAILED` (`STALE_PROCESSING`). Condition guards on **both** `status = :processing` AND `updated_at = :stale_ts` — a scan that finished in between makes the condition fail; the reaper can never clobber a live or finished scan |
| `UPLOAD_TIMEOUT` | `status = PENDING` and now > `created_at` + 960 s (presign expiry 900 s + 60 s grace — no in-flight upload can survive past this) and `HeadObject` → 404 | conditional → `FAILED` (`UPLOAD_TIMEOUT`) |
| `EVENT_NOT_RECEIVED` | same, but `HeadObject` → object exists | conditional → `FAILED` (`EVENT_NOT_RECEIVED`) — upload confirmed but the S3 event was lost (rare). Fix message: re-upload. Self-heal via Lambda self-invocation is documented as non-MVP (it would need `lambda:InvokeFunction` on itself; the claim makes it safe, but it is complexity for a rare path) |

**Approved semantics note:** `PENDING → FAILED` (the upload-timeout family) is an additive transition beyond the CONTRACTS.md text (`PENDING → PROCESSING → DONE | NEEDS_REVIEW | FAILED`); statuses, terminal-finality rules and JSON shapes are unchanged. Approved in the DECISIONS.md decision log, 2026-09-17.

### 5.5 Theorem — exactly-once pipeline execution

**Claim:** the pipeline body executes at most once per `scan_id`.

**Proof:** execution requires a successful conditional update transitioning `status` from `PENDING` to `PROCESSING`. DynamoDB conditional writes on the same item are serialized — an atomic test-and-set. Exactly one evaluation can observe `status = PENDING` (the winner transitions it); every later evaluation observes `PROCESSING` or a terminal value. This holds independent of event count, delivery order, or concurrency. ∎

**Liveness:** at-least-once delivery + the record-before-object causality (§5.4) ⇒ some delivery of the event claims successfully.

**Corollary (single-writer downstream):** results, summary and artifacts are each written by exactly one execution — torn writes are impossible by construction, and outputs-bucket keys need no conflict handling.

**Collision math:** `scan_id` space = 32⁶ ≈ 1.07 × 10⁹. Birthday collision at k scans ≈ k² / (2 × 1.07 × 10⁹): 1,000 scans → ~0.05%, 10,000 → ~4.7%. The `attribute_not_exists` condition catches any collision → regenerate; a wrong-scan overwrite is impossible.

**Reaper safety:** a false `STALE_PROCESSING` FAIL requires a scan legitimately still executing at 5-minute staleness — impossible: the claim refreshes `updated_at`, the pipeline budget is < 10 s (Feature 1 §1.8) and the Lambda hard cap is 60 s. P(reaper kills a live scan) = 0, by the timestamp condition plus margin.

### 5.6 Cost & latency budget

| Step | Cost | Latency |
|---|---|---|
| POST /upload (1 PutItem + local HMAC presign) | ~1 WCU | < 200 ms |
| Claim (1 conditional UpdateItem) | ~1 WCU | single-digit ms |
| Duplicate event, skipped | ~1 WCU | < 5 ms — noise level |
| Stale guards (rare paths only) | 1 conditional write | single-digit ms |
| GET /scans/{id} with `ConsistentRead` | 2 × RCU per poll | single-digit ms |

`ConsistentRead = true` on `GET /scans/{id}` (approved): eventual consistency could briefly show a finished scan as still PROCESSING, making the polling loop look broken. The cost remains negligible at polling volume (~50 reads/scan).

No new service is introduced; the 4-service lock (DECISIONS.md §5) holds.

### 5.7 Self-challenge (design attacked before approval)

| Attack | Outcome |
|---|---|
| Two concurrent duplicate events | atomic claim — exactly one winner |
| Late duplicate after DONE/FAILED | condition fails → skip |
| Lambda async retry after exception | FAILED already written in `finally` → retry skips |
| Hard kill (timeout/OOM before any write) | stuck PROCESSING → reaper converts to FAILED |
| Direct bucket PUT, no scan record | condition fails on non-existent item → skip; no phantom record |
| Content-type tampering | ContentType pinned in the signature → S3 403 |
| Same photo uploaded twice (two scan_ids) | two scans, both intended; second Bedrock call free via the ETag cache |
| Oversized/garbage upload | event `size` gate → FAILED before any download |
| Upload never completed | `UPLOAD_TIMEOUT` after presign expiry |
| Event lost though upload succeeded | `EVENT_NOT_RECEIVED` |

### 5.8 Implementation direction (translate, don't design)

1. `generate_scan_id()` — pure; charset from `ingestion.config`; validated against `^SC-[A-HJ-NP-Z2-9]{6}$`
2. `create_pending_record(...)` — PutItem with `attribute_not_exists(scan_id)`; collision → regenerate (max 3)
3. `presign_upload(key, content_type)` — thin wrapper over boto3; 900 s; ContentType signed
4. `claim_scan(scan_id, size_bytes)` — THE conditional update; returns `claimed: bool`, never raises on condition failure; the handler derives `scan_id` by parsing the S3 key (`uploads/{scan_id}.{ext}`), never from payload fields
5. `mark_terminal(scan_id, status, error)` — conditional write guarded on `status = :processing`
6. `reap_stale_processing(record)` / `reap_stale_pending(record, head_result)` — pure decision + conditional write; called from the GET route (Feature 7 wires the route)
7. `ingestion.config` — content types, size cap (20 MB), stale thresholds (5 min / 960 s), presign expiry (900 s), scan_id charset
8. Infra configs shipped verbatim (the agent copies, never designs): IAM policy JSON (uploads read + outputs write + DynamoDB rw on `scans` + Bedrock invoke + logs), uploads-bucket CORS JSON (PUT + Content-Type from the web origin), S3 trigger config (bucket, prefix `uploads/`, `ObjectCreated:*`), Lambda env vars (table name, buckets, region)
9. Handler branches on invocation type (Function URL event vs S3 event) — one Lambda, two invocation modes (DECISIONS.md §5)
10. Skipped duplicates must return success, never raise — raising triggers S3 retry noise (idempotency survives, but the delivery log turns to noise and the two-runs-clean property dies)

### 5.9 Acceptance criteria (fixture-driven, deterministic)

1. Same event delivered twice sequentially → exactly one pipeline execution; second returns success
2. Two claims raced (simulated concurrent) → exactly one wins, loser skips cleanly
3. Event for an object with no scan record → no record created (no phantom), skip logged
4. Late event after terminal status → skipped; the record is byte-identical before/after
5. `size` > cap → `FAILED` (`OVERSIZED_FILE`); the object is never downloaded
6. Pipeline exception → `FAILED` with error object written (`finally` block)
7. Reaper: stale PROCESSING → `FAILED` (`STALE_PROCESSING`); fresh PROCESSING → untouched; DONE with old `updated_at` → untouched (status condition)
8. PENDING + 960 s elapsed + HeadObject 404 → `FAILED` (`UPLOAD_TIMEOUT`); object exists → `FAILED` (`EVENT_NOT_RECEIVED`)
9. Wrong `content_type` or `label_width_mm ≤ 0` → `400` with the standard error body
10. 1,000 generated `scan_id`s all match the charset regex; forced-collision fixture → regeneration, no overwrite
11. Two runs of every fixture → identical output

---

## Feature 6 — Report Generator (annotated image, PDF/CSV)

### 6.1 Goal

Turn a completed pipeline run into the five downloadable artifacts — annotated image, PDF report, CSV, JSON, display image — such that (a) what the artifacts show is provably what the engine decided (**render fidelity**), and (b) identical inputs produce byte-identical artifacts (**determinism**).

### 6.2 The boundary — what this feature is NOT

The user-facing report card is the FRONTEND's render of the Scan Record (CONTRACTS.md §2); the frontend track builds it entirely from the contract and never reads this file. F6 produces only the export artifacts plus the two UI-enabling additions (`display_image`, `summary.found_declarations`). F6 runs in the same pipeline invocation as the rule engine and consumes **pipeline context** (results, field_status, exemption) — the record alone does not carry field_status, which is why `found_declarations` is computed here and stored (approved additive change).

### 6.3 Candidate approaches considered

**PDF generation:**

| Approach | Verdict | Reason |
|---|---|---|
| P1 — reportlab | **SELECTED** | pure Python, Lambda-layer friendly, proper tables, `invariant` mode gives reproducible bytes |
| P2 — fpdf2 | REJECTED | lighter, but weak table layout control |
| P3 — weasyprint / wkhtmltopdf / pandoc | REJECTED | native system deps — the same layer-hell rejection as OpenCV in Feature 2 |
| P4 — PIL-only PDF | REJECTED | PIL's PDF writer is image-only, no text layer |

**Annotation rendering:**

| Approach | Verdict | Reason |
|---|---|---|
| A1 — PIL draw, server-side | **SELECTED** | PIL already in the stack (Feature 2), deterministic, persists as an S3 artifact |
| A2 — OpenCV drawing | REJECTED | ~100 MB layer (Feature 2 precedent) |
| A3 — frontend-only boxes | REJECTED | contract requires a server-side artifact; browser rendering is not deterministic and leaves no downloadable annotated image |

### 6.4 The chosen design

**Canonical image (the coordinate guarantee).** The pipeline's single canonical processed image — EXIF-transposed, original resolution for photos; the page rendered at fixed 200 DPI for PDFs — is the same object the word index and every box refer to. F6 draws on that object: one coordinate space, by construction. The EXIF transpose happens upstream at preprocess, so a rotated phone photo cannot misalign boxes.

**Annotated image (PIL):**
- one rectangle per result with `box != null`, validated in-bounds against `extraction.image` (out-of-bounds → skip + log; report still generated — partial report principle)
- colors: FAIL red, PASS green, NEEDS_REVIEW amber (NA-with-box also amber)
- stroke width `max(3, image_width // 400)` — visible at 4K, not fat on small labels
- a small label chip above each box: rule_id + status
- **identical boxes grouped**: one rectangle, labels stacked (R5 and R8 share the MRP box in the contract's own example)
- legend banner prepended above the image (canvas extended upward, boxes drawn first on the original, then pasted): `7 PASS · 3 FAIL · 1 NA · 0 NEEDS_REVIEW` (exempt scans: `EXEMPT — Rule 26(a)`); documented consequence: annotated_image dimensions ≠ `extraction.image` dimensions when the banner is on
- saved as JPEG, fixed quality 85, EXIF stripped

**display_image (approved additive):** the canonical image resized to max edge 1600 px (only if larger), EXIF-stripped, JPEG q85 → outputs bucket. Public. Enables the UI's original/annotated toggle and the interactive box overlay (boxes + image dims already travel in the record).

**PDF report (reportlab, invariant mode):**
- page 1: the annotated image embedded full-width
- page 2+: report card — "found X of 7 declarations" (X = VERIFIED count from field_status), per-rule table (rule_id, name, citation, status, evidence, fix; `measurement` as compact JSON for R8–R10), tables auto-split across pages with repeated headers; verified unanchored fields carry an "unanchored-verified" tag
- exemption banner if `exemption.applied`; footer always: "This tool assumes non-exempt retail packaged goods." (Feature 4 §4.4)
- timestamps come from record fields (`created_at`) — inputs, never clock reads
- non-Latin glyphs (e.g. Devanagari evidence) → placeholder `[non-Latin text — see JSON report]`; JSON/CSV carry full fidelity
- multi-page PDF inputs: **first page only in MVP** (label artwork is single-page in practice), remaining pages ignored and noted in the report; multi-page = roadmap

**CSV:** header row + one row per result + summary row; RFC 4180 quoting (Python `csv` module); UTF-8 **with BOM** (Excel-safe).

**JSON:** the final scan record serialized.

**Ordering with Feature 5 (the single terminal write):** rule engine done → all five artifacts generated **in memory** (fail fast, no partial PUTs) → 5 S3 PUTs (bucket-level public-read policy on the outputs bucket, no per-object ACL) → ONE terminal write that populates `artifacts` + `summary` + `summary.found_declarations`. A terminal record therefore always references complete artifacts. Artifact generation/PUT failure: 1 retry (2 s backoff), then scan `FAILED` (`INTERNAL`) — honest, and Feature 5's claim theorem is untouched.

### 6.5 Theorems

**Render fidelity.** Claim: every box drawn corresponds to exactly one result with `box != null` (after in-bounds validation), and the PDF/CSV/JSON contain exactly the record's results. Proof: rendering is a pure function of (canonical image, results, field_status, exemption, config); F6 contains no independent decision logic, so divergence between report and verdicts is unrepresentable. With Feature 5's single-writer corollary there is no concurrent writer to race. ∎

**Byte-determinism.** Claim: same inputs → byte-identical artifacts. Proof: nondeterminism sources enumerated and removed — (1) reportlab `invariant` mode fixes CreationDate/document ID, (2) JPEG fixed quality + EXIF stripped, (3) no wall-clock in content (timestamps are record fields), (4) library versions pinned by the Lambda layer. Verified by fixture: two runs → identical bytes. ∎

### 6.6 Cost & latency budget

| Step | Time |
|---|---|
| Annotated JPEG (12 MP, PIL draw + save) | ~150–400 ms |
| display_image (resize + save) | ~50–100 ms |
| PDF (reportlab, 2 pages) | ~150 ms |
| CSV + JSON | ~5 ms |
| 5 × S3 PUT | ~500 ms |
| **F6 total** | **< 1 s** — pipeline stays inside the < 10 s budget (Feature 1 §1.8) |

Memory: 12 MP RGB ≈ 36 MB — comfortable at Lambda 1024 MB. reportlab ≈ +5 MB to the layer. No new AWS service; the 4-service lock holds.

### 6.7 Self-challenge (final round)

| Attack / gap | Resolution |
|---|---|
| GAP: original image not publicly accessible — UI cannot show a clean original or overlay boxes interactively | `display_image` artifact added (approved additive contract change) |
| GAP: "found X of 7" not derivable from the record alone (raw present ≠ VERIFIED) | `summary.found_declarations` added (approved additive contract change) |
| Box outside image bounds | validated → skip + log, report still complete |
| EXIF-rotated phone photo | canonical image transposed upstream — single coordinate space |
| Banner changes annotated_image dimensions | documented rule: banner extends the canvas upward; PDF embed and UI unaffected |
| R5 + R8 share one box | identical boxes grouped — one rectangle, stacked labels |
| Long evidence overflows PDF pages | reportlab table auto-split with repeated header |
| reportlab invariant-mode claim | verify-then-trust: fixture asserts byte-identical two-run output; layer pins versions |
| Devanagari in PDF | placeholder; reportlab cannot complex-script shape — full fidelity in JSON/CSV (BOM) |
| Exempt scan (Feature 4) | no boxes, exemption banner + footer, all rows NA |
| 12 MP memory spike | ~36 MB at 1024 MB Lambda |
| S3 PUT transient failure | 1 retry → then honest `FAILED` (`INTERNAL`); no partial artifacts referenced |
| Artifacts written but record write fails | orphan public files with deterministic keys — harmless, outputs are public by design |

### 6.8 Implementation direction (translate, don't design)

1. `render_annotated(canonical_image, results, config)` → PIL Image — pure; validates + groups boxes, draws, prepends banner
2. `render_display_image(canonical_image, config)` → PIL Image — pure; resize only if max edge > 1600
3. `build_pdf_report(scan_fields, results, exemption, found_declarations, config)` → bytes — reportlab, invariant mode on
4. `build_csv_report(results, summary)` → bytes with BOM
5. `sanitize_pdf_text(s)` → Latin-safe with `[non-Latin text — see JSON report]` placeholder
6. `reports.config` — colors, stroke scale, banner format, JPEG quality, display max edge, PDF DPI, page margins, retry/backoff
7. outputs-bucket public-read bucket policy — verbatim infra config (the agent copies, never designs)
8. all five artifacts generated before any PUT (fail fast in memory)
9. no clock reads anywhere in F6 — timestamps come from record fields only
10. `found_declarations` computed from the field_status map (count VERIFIED of the seven declaration fields), passed into summary at the terminal write

### 6.9 Acceptance criteria (fixture-driven, deterministic)

1. Clean label with mixed verdicts → boxes exactly match results with `box != null`, colored red/green/amber; zero boxes for box-null results
2. Out-of-bounds box fixture → skipped + logged; report otherwise complete
3. R5 + R8 identical-box fixture → one rectangle, two stacked labels
4. Two runs → all five artifacts byte-identical (asserts invariant mode + fixed encoder settings)
5. Devanagari evidence fixture → PDF placeholder, JSON/CSV full text, CSV opens correctly in Excel (BOM)
6. Exempt scan → no boxes, exemption banner + footer, every row NA
7. Artifact PUT failure (simulated) → 1 retry → `FAILED` (`INTERNAL`); no terminal record references partial artifacts
8. 12 MP input → display_image max edge 1600, EXIF stripped; already-small image → pixel dimensions unchanged
9. 5 of 7 declarations VERIFIED → PDF shows "found 5 of 7 declarations" and `summary.found_declarations = 5`
10. Multi-page PDF fixture → page 1 processed, note present in report
11. Banner text always equals summary counts (including the exempt case)
12. Two runs of every fixture → identical output

---

## Feature 7 — API + Storage (history/search/stats)

### 7.1 Goal

Serve the four read routes of the frozen API surface (CONTRACTS.md §3) over the single `scans` table — ordered history, search, filters, pagination, stats, artifact serving — with **zero contract changes** and with no route able to corrupt the state machine.

### 7.2 The boundary

`POST /upload` is Feature 5's; the router dispatches by (method, path) and forwards there. Feature 5's stale guards are defined in F5 §5.4 — F7 wires them into `GET /scans/{id}`. Feature 6 produces artifacts; F7 serves them. F7 adds no API route, no contract field, no AWS service.

### 7.3 Traps

1. **Random PK → no ordered list.** `scan_id` is random (`SC-` + 6 chars), PK is `scan_id` — newest-first history is impossible from the base table without an index.
2. **No native fuzzy search.** GSI key conditions support equality (PK) and `begins_with` (SK) only — no `contains`. A real search service (OpenSearch) is a 5th service — banned by the lock.
3. **`rule_id` filter targets a nested list.** FilterExpression cannot match "any `results[]` element with rule_id = R5 AND status = FAIL" — nested list matching is not supported.
4. **Stats drift.** Parallel counter items can desync from the records on any partial failure — a wrong-stats-forever bug class.
5. **Fat records.** Extraction is inline (`extraction`, CONTRACTS.md §2) — `limit=100` ≈ 1 MB response; the Function URL sync limit (6 MB) holds, but must be a known quantity.

### 7.4 Candidate approaches considered

**Ordered history + pagination:** H1 — GSI-1: PK constant `"SCAN"`, SK `created_at#scan_id`, query `ScanIndexForward=false` (**SELECTED** — indexed, O(page), LastEvaluatedKey = native cursor) · H2 — full Scan + in-memory sort every request (REJECTED — O(n) per view, hand-rolled pagination) · H3 — timestamp-prefixed IDs (REJECTED — `scan_id` format frozen in CONTRACTS.md §2).

**`query` search:** S1 — GSI-2 brand-prefix fast path + capped Scan-contains fallback (**SELECTED** — both real fuzzy and indexed common case) · S2 — Scan + Filter only (REJECTED as primary — O(n) on every search; kept as the fallback leg) · S3 — OpenSearch/Comprehend (REJECTED — 5th service, lock violation).

**Stats:** T1 — on-demand aggregation, 60 s warm cache (**SELECTED** — no drift class exists; no F5 interplay) · T2 — counter items with atomic ADD (REJECTED — would force F5's locked `mark_terminal` into a transaction, and creates the drift bug class) · T3 — aggregation in GSI (REJECTED — DynamoDB has no aggregate queries).

**Reports serving:** R1 — 302 redirect to the public S3 URL (**SELECTED** — CONTRACTS.md itself: "Artifacts are S3 keys, served via their public URLs"; Lambda never proxies bytes) · R2 — stream through Lambda (REJECTED — bandwidth + timeout risk, zero benefit).

### 7.5 The chosen design

**Storage schema — internal attributes (never in responses):** every scan record carries at write time:

- `gsi1_pk` = `"SCAN"` (constant), `gsi1_sk` = `created_at#scan_id` → **GSI-1** (history index: newest-first, paginated)
- `gsi2_pk` = `"BRAND"` (constant), `gsi2_sk` = `brand_key#created_at#scan_id` → **GSI-2** (brand search), where `brand_key` = `brand_guess` lowercased + punctuation-stripped; `product_key` = same normalization on `generic_name` (base-table attribute, used by the fallback filter)
- `failed_rules` = String Set of FAIL rule_ids (e.g. `{"R5","R8"}`) — **the rule_id-filter solution**: FilterExpression `contains(failed_rules, :rule)` works on sets. A scan with zero FAILs OMITS the attribute (DynamoDB cannot store empty sets; `contains` on a missing attribute is a no-match — exactly the semantics wanted).

All computed at the terminal write from pipeline results. F5's conditional-guard design is unchanged — attributes only.

**Routes:**

- `GET /scans` — default: GSI-1 query (`ScanIndexForward=false`), newest first. `status` → same query + FilterExpression. `rule_id` → same + `contains(failed_rules, :rule)`. `query` → (1) GSI-2 `begins_with(gsi2_sk, :q_normalized)` fast path (brand prefix); (2) empty result → base-table Scan + `contains(brand_key, :q) OR contains(product_key, :q)` (true fuzzy + product names) — **the fallback LOOPS** (bounded, max 10 pages) until `limit` RESULTS are collected or the table ends: Scan's `Limit` counts scanned items, not filtered results — the contract's `limit` is a result count. Combined params compose with AND. `last_key` = base64(ExclusiveStartKey) — opaque cursor; decode failure or invalid shape → `400 BAD_REQUEST`.
- `GET /scans/{id}` — GetItem, `ConsistentRead=true` (F5-approved); reaper guards wired (F5 §5.4); unknown id → `404`.
- `GET /stats` — Scan + aggregate in Lambda (ProjectionExpression: summary/results/failed_rules only), 60 s in-memory warm cache per Lambda instance. **Definitions:** `total_scans` = all records (any status); `overall` + `by_rule` = terminal scans' results only (PENDING/PROCESSING/FAILED carry null results); `by_rule` lists only rules with ≥1 scan; `most_failed_rules` = FAIL counts descending. Multiple warm instances each caching = harmless (idempotent read).
- `GET /reports/{scan_id}.{format}` — GetItem: non-terminal or unknown → `404` (contract: "404 if the scan hasn't finished"); terminal → `302` + `Location: <public S3 URL>` with the artifact's Content-Type set at upload time (F6 infra config). Frontend uses direct links (no CORS needed for navigations; bucket CORS config included anyway for XHR use).

**Response serializer:** explicit whitelist — `gsi1_pk`, `gsi1_sk`, `gsi2_pk`, `gsi2_sk`, `brand_key`, `product_key`, `failed_rules` never appear in any response; the contract shape is byte-exact.

**Router:** dispatch by (method, path); trailing slash stripped; unknown path → `404`; known path + wrong method → `405`; every error in the contract's error format (CONTRACTS.md §3).

### 7.6 Theorems

**Read purity.** Claim: no route mutates scan state except the F5-approved stale guards. Proof: enumerate the routes — GetItem, Query, Scan, redirect are read-only; the reaper's writes are conditional and timestamp-guarded (F5 §5.4, already proven). No GET sequence can corrupt the state machine. ∎

**Pagination completeness.** Claim: pages contain no duplicates and no gaps. Proof: LastEvaluatedKey resumes at exactly the next item in index order; GSI-1's order is deterministic (`created_at#scan_id` lexicographic — ISO 8601 sortable + unique tie-break). Documented caveat: inserts landing on a page boundary during pagination may appear or shift — eventual consistency, irrelevant at hackathon scale. ∎

**Stats non-drift.** Claim: stats cannot disagree with the records. Proof: stats are a pure aggregation over the table — there is no parallel mutable state to desynchronize. The counter design's failure mode (partial-update drift) is unrepresentable here. The only staleness is the 60 s cache window, a documented freshness bound. ∎

**Storage-scale note (documented ceiling):** GSI-1 places all scans on one partition key (writes and queries well within partition limits at ≤ a few thousand scans); the Scan fallback and stats aggregation are O(table). This design is sized for the hackathon benchmark (~100–1000 scans); beyond a few thousand, search and stats need a redesign (OpenSearch / counters + transactions) — roadmap, not MVP.

### 7.7 Cost & latency budget

| Route | Latency | Cost |
|---|---|---|
| GET /scans/{id} | < 20 ms | 1–2 RCU (consistent) |
| GET /scans (GSI-1) | ~30–50 ms | page RCU |
| GET /scans ?query (fallback leg) | ~0.5–2 s @ 1000 scans | O(n) reads — ceiling documented |
| GET /stats | ~50 ms warm / 1–2 s cold @ 1000 | O(n) cold, cached warm |
| GET /reports | < 20 ms + browser fetches S3 | 1 RCU |

No new service; the 4-service lock holds. One table + 2 GSIs, per DECISIONS.md §5.

### 7.8 Self-challenge (final round — findings incorporated)

| Attack / gap | Resolution |
|---|---|
| Scan `Limit` counts scanned, not filtered results | fallback LOOPS (bounded 10 pages) until `limit` results — contract semantics preserved |
| Empty String Set unrepresentable in DynamoDB | zero-FAIL scans OMIT `failed_rules`; `contains` on missing attribute = no-match = correct |
| `total_scans` vs `overall` scope ambiguity | defined: total = all records; overall/by_rule = terminal results only |
| GSI eventual consistency | polling path uses base-table consistent read (F5); GSI lag affects display-only routes — documented |
| GSI-1 single hot partition | within partition limits by 1000× at hackathon scale; ceiling documented |
| Nested-list filter impossible | `failed_rules` String Set written at terminal — O(1) filter |
| Cursor tampering | decode/shape failure → 400 |
| Reaper race on GET route | F5 timestamp-guarded conditional — already proven |
| Internal keys leaking | whitelist serializer + fixture asserting absence |
| Combined query + status + rule_id | filters compose with AND on both search legs |
| 1 MB response at limit=100 | inside the 6 MB Function URL sync limit; `limit` max frozen by contract |
| Stats cache divergence between instances | idempotent read; worst case one stale window |

### 7.9 Implementation direction (translate, don't design)

1. `router.py` — (method, path) → handler map; strip trailing slash; 404/405 per contract error format
2. `list_scans(params)` — GSI-1 query + composed FilterExpressions + cursor encode/decode
3. `search_scans(params)` — GSI-2 prefix leg; capped-loop Scan fallback leg; merge-free (one leg runs per request)
4. `get_scan(id)` — consistent GetItem + reaper guard invocation (F5 §5.4 functions)
5. `get_stats()` — Scan + aggregate (pure fold over records); 60 s warm cache
6. `redirect_report(id, fmt)` — status check → 302 Location
7. `serialize(record)` — whitelist serializer emitting the contract shape only
8. `normalize_key(s)` — lowercase + punctuation strip; used at write AND query time (one function, never two)
9. `api.config` — cache TTL, fallback page cap (10), pagination max (100), GSI constants
10. Infra configs verbatim: GSI-1/GSI-2 definitions (key schemas, projections ALL), outputs-bucket CORS (GET), table name env vars

### 7.10 Acceptance criteria (fixture-driven, deterministic — moto-backed)

1. 25 scans inserted in mixed order → GET /scans returns newest first; pages via last_key; union = all 25, no duplicates, no gaps
2. `status` filter → only matching records; pagination correct
3. `rule_id=R5` → exactly the scans whose failed_rules contains R5; zero-FAIL scan never appears
4. `query="haldiram"` → GSI-2 prefix leg hits; mid-string query and product-name query → fallback leg hits; both legs case/punctuation-insensitive
5. `query` + `status` + `rule_id` combined → AND semantics on both legs
6. Garbage/invalid-shape `last_key` → 400 with contract error body
7. Stats fixture with known records → total_scans = all records; overall/by_rule from terminal results only; most_failed_rules sorted desc; empty DB → total 0, by_rule {}
8. No response anywhere contains an internal key (assert gsi1_pk, gsi2_sk, brand_key, product_key, failed_rules absent)
9. GET /reports: PENDING → 404; terminal → 302 + Location to the S3 URL; unknown id → 404; bad format → 400
10. Stale-PROCESSING fixture polled via GET /scans/{id} → FAILED (STALE_PROCESSING) — reaper wired
11. Unknown path → 404; wrong method → 405; every error body matches the contract error format
12. Fallback leg returns exactly `limit` results when matches exist (loop semantics)
13. Two runs of every fixture → identical output

---

## Feature 8 — Benchmark Harness (accuracy/coverage methodology)

### 8.1 Goal

Produce the demo's numbers honestly: rule-level accuracy and coverage, measured on 80–100 real supermarket labels against hand-verified ground truth (DECISIONS.md §2), with accuracy and coverage reported as **separate numbers** (the core principle, operationalized) and every claim carrying an exact binomial confidence bound.

### 8.2 The boundary — what the benchmark can and cannot claim

The benchmark validates **system vs codified spec** (the decision tables of Features 2–4), NOT spec vs law. Where the law is ambiguous, ground truth follows the documented interpretation registry (F3 §3.4) and the report discloses how often each interpretation fired (watch-list). Spec-vs-law defensibility is a documentation argument (gazette citations, interpretation registry), not a measurable one — stated in the report itself.

**Labeling authority:** ENGINEERING.md's decision tables (F2 §2.4–2.5, F3 §3.3, F4 §4.5) — the same tables the code implements. `backend/docs/CHECKS.md`, written after the proven features, is their compilation; F8 invents no new spec.

### 8.3 Metric definitions (exact)

For every (label, rule): ground truth ∈ {PASS, FAIL, NA-truth (e.g. embossed R10), NA_EXEMPT}; system verdict ∈ {PASS, FAIL, NA, NEEDS_REVIEW}. Truth must be definitive wherever the law + spec give an answer — an unsure labeler triggers adjudication, never a NEEDS_REVIEW truth.

- D = {(label, rule) : system ∈ {PASS, FAIL} AND truth ∈ {PASS, FAIL}}
- **Accuracy = matches(D) / |D|** — a wrong verdict is only definable on a definitive verdict (the core principle).
- **Coverage = |D| / |truth-definitive checks|** — a system NA/NEEDS_REVIEW on truth-definitive is a coverage loss, never an accuracy error.
- **False-definitive counter** — system definitive where truth is NA-truth (embossed R10): reported separately, never folded into accuracy.
- **ε_ocr (honesty clause, F1 §1.5)** — VERIFIED fields whose raw contradicts the ground-truth printed value (normalization: casefold, whitespace/punctuation-insensitive; numerals exact). Target: 0. Requires per-field ground truth (approved).
- **Exempt cohort** — exemption detection on ≤10 g sachets: counts, not percentages (N too small for a CI).
- **Stability (sub-run)** — verdict agreement across fresh, cache-bypassed extractions on a 20-label subset.

### 8.4 Traps

1. **FAIL-sample scarcity** — supermarket labels skew compliant; without deliberate stratification, FAIL accuracy is underpowered.
2. **Authority circularity** — a shared misreading of the law would score "correct"; resolved by the §8.2 boundary statement.
3. **Labeler error rate** — humans err; disagreements are disputes (adjudication), not automatic system bugs.
4. **Nondeterminism** — Bedrock extraction varies per run; the ETag-keyed cache freezes one sample; verdicts do not depend on the sample (gauntlet). Version drift between local and Lambda-layer Tesseract/geometry must be pinned away.
5. **R8 truth uncertainty** — hand measurement of 1–4 mm numerals carries ~±0.3 mm of its own error.

### 8.5 Candidate approaches considered

| Approach | Verdict | Reason |
|---|---|---|
| BW1 — local deterministic replay over cached extractions | **SELECTED** | re-runs free, no AWS flakiness, infra bugs separated from logic bugs |
| BW2 — live end-to-end runs every time | REJECTED as primary | cost + variance + conflates infra with logic; one final live run retained (approved) |
| BW3 — manual spreadsheet scoring | REJECTED | non-reproducible, error-prone |

Ground truth storage: per-label JSON in the CONTRACTS.md §5 expected-results shape — benchmark labels double as regression fixtures. One collection, two jobs.

### 8.6 The chosen design

**Collection protocol.** 80–100 real supermarket labels (DECISIONS.md §2): plain-background photos where possible + physical measurements (label width; PDP width × height for the area class; numeral heights for R8 via calipers or artwork specs) + the 7 declaration fields' printed values transcribed + per-rule expected verdicts — labeled independently by **2 people** against the decision tables; disagreements adjudicated by a third. Truth records measured values WITH uncertainty; R8 labels whose measured height lies within **±0.3 mm of the legal threshold are excluded from R8 accuracy** (truth itself boundary-uncertain — F2's boundary-zone philosophy applied to the labeling side; they remain in the coverage denominator). Stratification minimums (approved): ~10% Hindi labels, ≥10 known R5 violations, ≥5 exempt sachets, ≥10 uncalibrated photos, ≥5 PDF artworks.

**Initial pass.** A driver script uploads the label set through the deployed stack (`POST /upload` → PUT → poll); scan records are harvested — the extraction is inline in each record (CONTRACTS.md §2), so harvested records ARE the cached extractions. Doubles as a live-stack exercise.

**Harness.** `benchmark/labels/` (images + ground-truth JSON) · `run.py` (offline replay: harvested extraction → gauntlet → rule engine; deterministic; Tesseract/geometry pinned to Lambda-layer versions) · `score.py` (pure: results × truth → metrics) · `report.py` (markdown + JSON). Dispute export: disagreements CSV → adjudicate → update truth → re-score. Any wrong verdict found is a BUG (gauntlet/config) — root-caused, fixed, re-run, fix logged in the report — BEFORE the demo.

**Stability sub-run (approved).** 20 labels, fresh cache-bypassed extraction (`BENCHMARK_SKIP_CACHE=1`, default off, fixture asserts the default), verdicts compared: definitive verdicts expected stable; coverage may vary. ~$0.20.

**Live validation (approved).** After the local benchmark passes: one 10-label end-to-end run on the deployed stack — the demo's numbers cite the deployed system (Ship It judging, DECISIONS.md §0).

**Report contents.** Headline accuracy + Clopper-Pearson 95% CI; coverage (+CI); N labels / N rule-evaluations; ε_ocr count; per-rule table (counts + CI, never a bare percentage); language cohorts (en/hi); path cohorts (photo calibrated / uncalibrated / PDF); watch-list fire counts (1500 g interpretation, sticker MRP, R10 contrast band); false-definitive counter; adjudication log (truth corrections count → labeler error-rate estimate); stability agreement. The DECISIONS §2 90 %-accuracy target is stated next to the measured value — a target, never a pass/fail gate; the writeup quotes actual numbers.

### 8.7 The math

- **Zero-wrong reporting:** 0 wrong in N → report "0/N, 95% CI upper ≈ 3/N" (Clopper-Pearson via `scipy.stats.beta.ppf` — already in the stack). At N = 900: upper ≈ 0.33%. Never report a bare "100%".
- **Per-rule:** ~80–100 samples → 0 wrong in 80 → upper ≈ 3.7% — too wide to headline; per-rule ships as counts + CI, the overall number is the headline.
- **Coverage:** expected 85–95% (F1 §1.7), CI ≈ ±2–3% at N ≈ 1000.
- **R8 boundary exclusion** keeps uncertain TRUTH out of the accuracy denominator — symmetric to the system's own boundary rule.

### 8.8 Cost & schedule reality

Extraction ≈ $1–2 total (DECISIONS.md §4); re-runs free (cache); stability ≈ $0.20. The real cost is human: full verification ≈ 10–15 min per label per labeler. Phased: first ~30 fully-verified labels by day 2, remainder by day 3. The report always states the actual verified N — never inflated; whatever N is verified at recording time is what ships.

### 8.9 Self-challenge (final round — findings incorporated)

| Attack / gap | Resolution |
|---|---|
| Truth authority circularity (shared misreading scores "correct") | §8.2 boundary: benchmark = system vs spec; spec-vs-law = documentation argument |
| backend/docs/CHECKS.md written after the proven features | labeling authority = ENGINEERING decision tables (F2/F3/F4); CHECKS.md compiles them 1:1 |
| R8 truth uncertainty (±0.3 mm near thresholds) | boundary-truth labels excluded from R8 accuracy, kept in coverage denominator |
| Labeler unsure → NEEDS_REVIEW truth | forbidden: truth is definitive or adjudicated |
| Cache-bypass flag leaking into production | env var default off + fixture asserts the default |
| Same bytes → same ETag → forced-fresh trick fails | explicit `BENCHMARK_SKIP_CACHE` flag (benchmark-only) |
| Initial extraction needs AWS anyway | deployed-stack initial pass; records harvested via the API (extraction inline) |
| Only ~40 labels verified by demo time | report states actual N — honesty over inflation |
| Wrong verdict found late | that is the harness working: root-cause, fix, re-run, log — before the demo |
| Exempt cohort too small for a CI | counts only, no percentages |
| Duplicate label images in collection | dedupe by ETag at collection time |

### 8.10 Implementation direction (translate, don't design)

1. `collect_driver.py` — uploads the label set through the deployed stack via the CONTRACTS.md §3 API only; polls; harvests records
2. `run.py` — offline replay: harvested extraction JSON → gauntlet → rule engine → results (pure; pinned versions)
3. `score.py` — pure: (results, ground_truth) → metrics dict (§8.3 definitions as one switch; no new logic)
4. `report.py` — metrics → markdown + JSON (the demo's numbers)
5. Clopper-Pearson via `scipy.stats.beta.ppf` in a single helper
6. `ground_truth.schema.json` — per-label shape (verdicts, field values, measurements + uncertainty, exemption, notes); validated on load by pytest
7. `disputes()` — export disagreements CSV for adjudication
8. `benchmark.config` — normalization rules, R8 boundary (±0.3 mm), stratification minimums, stability subset (20), live subset (10)
9. `BENCHMARK_SKIP_CACHE` env flag — default off; fixture asserts the default; benchmark-only
10. Two-run determinism assertion built into the harness entry point

### 8.11 Acceptance criteria (fixture-driven, deterministic)

1. `score.py` on synthetic results × truth with known counts → exact expected metrics (a unit fixture per definition row)
2. ε_ocr fixture: wrong printed value + gates passed → counted; correct value → not counted
3. Boundary R8 truth (measured within ±0.3 mm of the threshold) → excluded from accuracy, present in the coverage denominator
4. Exempt label → exemption cohort counts; absent from the accuracy denominator
5. The report includes: accuracy + CI, coverage, ε_ocr, per-rule counts + CI, cohorts, watch-list, false-definitive counter, adjudication log, N
6. Dispute flow: re-scoring after a truth update changes the affected metrics
7. Stability: two extractions differing in raw text → identical definitive verdicts (fixture-simulated)
8. `BENCHMARK_SKIP_CACHE` default off asserted by fixture
9. The harness runs offline — zero network calls after harvesting
10. Two full harness runs → identical report bytes

---

## Feature 9 — Extraction Module (Bedrock client)

### 9.1 Goal

The single model job (DECISIONS §4): read the canonical image and emit the Extraction JSON (CONTRACTS §1 — 7 declaration fields + brand_guess) with boxes, or fail honestly. No verdict logic lives here — the gauntlet judges every claim (F1).

### 9.2 The chosen design

- **One Haiku call** via the Bedrock **Converse API with toolConfig** — a single tool `submit_extraction` whose input_schema IS the CONTRACTS §1 shape. The model cannot return anything but schema-valid JSON; most of G0 is enforced at the API boundary.
- **G0 (code-side, defense in depth):** jsonschema validation against CONTRACTS §1; failure → the fallback trigger.
- **Fallback trigger (locked — decision log 2026-09-18):** G0 schema-fail OR ≥ 2 of the 7 declaration fields with confidence < 0.60 → ONE Sonnet retry, same prompt. One weak field is the gauntlet's job (NEEDS_REVIEW); two means the whole read is suspect. Still failing → scan `FAILED` (`EXTRACTION_FAILED`).
- **Cache:** ETag-keyed (F1 §1.9 item 7) — a hit skips both calls.
- **Model IDs** (config, defaults — DECISIONS §9 item 3 stays open for final wiring): Haiku `anthropic.claude-3-5-haiku-20241022-v1:0`, Sonnet `anthropic.claude-sonnet-4-20250514-v1:0`.

### 9.3 The prompt (verbatim — the agent copies, never redesigns)

"You are reading the principal display panel of an Indian packaged commodity label. Extract these seven declaration fields exactly as printed, plus a brand guess: manufacturer_name, manufacturer_address, generic_name, net_quantity, mfg_date, mrp, consumer_care. For each field return: raw (the exact printed substring — transcribe only, never infer or complete), parsed (mrp: rupees number; net_quantity: {value, unit in g|kg|ml|L|pcs}; mfg_date: MM/YYYY as printed; consumer_care: {phone, email}; null if not printed), confidence (0-1), box ([x, y, width, height] in pixels, covering the field's printed text). Also return brand_guess: the brand name exactly as printed, or null. Return null for any field not printed. Output only the tool call."

### 9.4 Vision input handling

The canonical image (Feature 10) is sent full-resolution — boxes come back in its coordinate space, no rescaling drift. Bedrock's ~5 MB image limit: if the canonical JPEG (quality 85) exceeds it, downscale deterministically to a 3500 px long edge and scale every returned box by the exact recorded factor (affine; boxes stay integers). The 20 px/mm geometry floor is unaffected — geometry reads the canonical image, not the LLM copy.

### 9.5 Cost & latency budget

| Path | Time | Cost |
|---|---|---|
| Haiku single call (typical) | 2–5 s | <$0.01 |
| Haiku + Sonnet retry (worst) | 5–9 s | <$0.02 |
| Cache hit | < 10 ms | free |

Worst case (retry + OCR 1–3 s) ≈ up to 12 s — above the 10 s target, inside the 60 s Lambda cap with the same 5-minute reaper margin; the typical path is 3–8 s. No new service; the 4-service lock holds.

### 9.6 Implementation direction (translate, don't design)

1. `extract(canonical_image, config) -> Extraction JSON or raise ExtractionError` — behind one interface (DECISIONS §4 lock); models swappable via env
2. `prompt.txt` — the §9.3 text, loaded as a file, never inlined in code
3. `schema.py` — the CONTRACTS §1 shape as jsonschema; G0 = `validate()`
4. `fallback.py` — the trigger rule (G0 fail OR ≥ 2 fields < 0.60) as a pure function
5. cache get/put wired (F1 §1.9 item 7)
6. Bedrock client errors (throttle, access, timeout) → `ExtractionError` → scan `FAILED` (`EXTRACTION_FAILED`) via F5's try/finally

### 9.7 Acceptance criteria (fixture-driven)

1. Schema-valid fixture → one Haiku call, valid Extraction JSON
2. Deliberately malformed response (mocked) → Sonnet retry → valid JSON
3. Both fail → scan `FAILED` (`EXTRACTION_FAILED`), no partial record
4. Weak-read fixture (2 fields < 0.60) → retry fires; 1 weak field → no retry (the gauntlet's job)
5. Cache-hit fixture → zero Bedrock calls
6. Oversize-image fixture → deterministic downscale, boxes scaled exactly
7. Two runs (cache off) → schema-valid both times; verdicts unchanged (gauntlet independence)

---

## Feature 10 — Preprocess (canonical image)

### 10.1 Goal

Produce the pipeline's single canonical processed image — the object every box, the word index, the geometry and the reports refer to (F6's coordinate guarantee: "the EXIF transpose happens upstream at preprocess").

### 10.2 The chosen design

- **Photo:** PIL open → `ImageOps.exif_transpose` (a rotated phone photo cannot misalign boxes) → RGB. Original resolution preserved (F2 §2.5: uploads must not be downscaled below the 20 px/mm floor).
- **PDF:** page 1 only, rendered at fixed 200 DPI — F6's locked choice (multi-page is first-page-only MVP with the note in the report). Renderer: **PyMuPDF (fitz)** — a pure wheel, no system deps (the same layer-hell rejection as OpenCV in F2 §2.6); pdftoppm/poppler REJECTED. The word index comes from the pdfplumber text layer (F1), not the raster; the raster serves vision (F9) and annotation (F6).
- **DPI note (pre-empting the reviewer):** 200 DPI ≈ 7.9 px/mm is below F2's 20 px/mm floor — no conflict: the floor governs photo-path pixel measurement; PDF R8 measures exact mm from pdfplumber char boxes (ε = 0). The render's DPI only affects vision quality.
- Pure function; deterministic; same input bytes → identical output bytes (fixed encoder settings).

### 10.3 Implementation direction (translate, don't design)

1. `preprocess(raw_bytes, content_type) -> canonical image` — pure, own module (T1.9)
2. Photo branch: exif_transpose + RGB; PDF branch: PyMuPDF page 1 @ 200 DPI (zoom = 200/72)
3. PyMuPDF joins the Lambda layer (T0.6), version-pinned (benchmark determinism, F8 trap 4)

### 10.4 Acceptance criteria (fixture-driven, deterministic)

1. EXIF-rotated JPEG → canonical output upright; downstream boxes align
2. Two-page PDF → page 1 rendered; page count noted for the report (F6's multi-page note)
3. Vector PDF → 200 DPI raster + pdfplumber word index from the same page, consistent coordinates
4. Two runs of every fixture → byte-identical output
