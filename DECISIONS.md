# DECISIONS.md — Source of Truth

**Project:** LabelCheck (working name — final name TBD)
**What it is:** Software system to check compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011 by scanning products, images and labels.

**One line:** label photo/PDF in → AI reads it (extraction only) → deterministic rule engine judges it against LMPC Rules 2011 → compliance report card out: pass/fail/NA per rule, exact clause citation, violations highlighted on the label image, fix-it guidance per violation.

**Rule for this file:** every decision marked LOCKED is final — changing it requires the whole team to agree and an entry in the log at the bottom. If any other document or chat contradicts this file, this file wins.

---

## 0. Context — the two events, one project

| | Event | Format | What we submit |
|---|---|---|---|
| 1 | **SIH 2026, PS SIH26034** (Ministry of Consumer Affairs, Food & Public Distribution) | Internal round: presentation | PPT: Problem → Gap → Solution → Architecture → Innovation → Demo → Impact |
| 2 | **WeMakeDevs × AWS Bharat Builds Tour — Stop 1 "First Commit", Sept 17–20, 2026** (hybrid: online anywhere in India + optional Bangalore Sept 19) | 4-day build, teams of 1–4 | Public repo + 2–3 min demo video + short writeup |

Event rules that shape everything:
- [LOCKED] **Project work (code/repo) starts Sept 17 only.** Repo history must match the event window — prior work disqualifies the team. Planning, setup, learning before that is allowed.
- [LOCKED] **Judging — official 5 criteria:** (1) **Idea & impact** — real problem, what changes for the people on the other side; "a small problem solved well beats a big one solved vaguely". (2) **Built on AWS** — mandatory for any prize; Ship It (deployed) is where the grand prize is decided, architecture + cost judged there. (3) **Learning counts towards the score** — the writeup must tell what we learned over the 4 days. Our team being new to S3/Lambda/DynamoDB is a genuine strength to show here, not something to hide. (4) **Execution** — "one feature that runs beats five that almost do". (5) **Demo video** — 3 min recorded: what it does, who it is for, and where AWS fits.
- [LOCKED] **Judging is video-only** (no live demo): anything the 3-minute video doesn't show doesn't count — the video must explicitly show where AWS fits.
- [LOCKED] **Submit early, keep improving until the deadline.** Late submissions are not scored.
- [LOCKED] We enter the **Ship It track** (deployed live on AWS). Best UI is a separate prize we also aim for.
- [LOCKED] AI coding tools allowed but **must be named in the writeup**. Writeup must cover: the problem, the build, where AWS fits, and what we learned.
- [LOCKED] Prizes/credits: selected deploying teams get credits from the organizers; each verified participant gets USD 100 AWS credits. WeMakeDevs account + verified AWS Builder Center profile required per participant.

## 1. Why this problem (problem statement facts)

- [LOCKED] LMPC Rules 2011 = the real law: 34 rules, 7 chapters, 7 schedules. **The checkable content for us lives in Chapter II, Rules 6–17** — everything else (wholesale, export, registration, penalties) is out of scope for the MVP.
- [LOCKED] Pain is two-sided: enforcement is manual and can't scale; manufacturers (D2C brands, MSMEs) have no pre-print self-check tool.
- [LOCKED] Positioning: **an assist / self-check tool — NOT a legally certified replacement for inspectors.** This sentence goes in the pitch as-is.

## 2. Product scope

- [LOCKED] **3 core features:**
  1. Scan → extract → 11 codified checks → report card (pass/fail/NA per rule, exact citation, annotated image with red/green boxes)
  2. Fix-it guidance per violation (exact required wording, required minimum letter height for the pack size)
  3. Report + history: downloadable PDF + JSON/CSV export (SIH demands "editable formats"), scan history with search, light stats view (scans, most-failed rules)
- [LOCKED] **Benchmark:** collect 80–100 real supermarket labels, hand-verify ground truth, report accuracy in the demo (target: 90%+ rule-level accuracy). This is a first-class deliverable, not an afterthought.
- [STRETCH — only if core is done] Cognito auth + role-based access; Second Schedule standard pack sizes (e.g. bottled water only in listed volumes).
- [LOCKED] **Photo-path product scope:** flat rectangular packets (chips, biscuits, namkeen, masala) and cartons/boxes only — the geometry math's planar assumption (whole front face at one scale) is valid for these; curved surfaces (bottles, jars) break it and are roadmap. The PDF/artwork path supports any shape (artwork is flat by definition).
- [LOCKED — roadmap, not MVP] wholesale/export packages (Chapter III/IV), full exemption matrix, e-commerce listing checks, FSSAI labelling, mobile app, batch upload. Post-hackathon: ship as self-serve compliance SaaS for D2C brands; FSSAI + e-commerce norms as expansion.

### Differentiation (why this is not a ChatGPT wrapper)

| Generic LLM chat | LabelCheck |
|---|---|
| Interprets rules from memory, inconsistent verdicts, invents rule numbers | Deterministic rule engine — same label, same verdict, exact sub-rule cited |
| Reads text, can't measure | Geometry checks: numeral heights (Rule 7), clear space (Rule 8), contrast (Rule 9) measured from pixels |
| A paragraph of prose | Structured report card + annotated image + PDF/JSON/CSV exports |
| One label at a time, no memory | Persistent history, search, stats |
| No accountability | Every check maps to a codified rule clause a human can verify |

## 3. The 11 codified checks (verified against the rulebook gazette text)

| # | Check | Rule | Method |
|---|---|---|---|
| R1 | Manufacturer/packer/importer name + complete address (street/city/state or PIN) | 6(1)(a), 10(1) | extraction + format |
| R2 | Common/generic name of commodity | 6(1)(b) | extraction |
| R3 | Net quantity in correct unit (<1kg → grams, <1L → ml; no "dozen/score/gross") | 6(1)(c), 13 | extraction + format |
| R4 | Month & year of manufacture, valid format (MM/YYYY, MON/YYYY or words) | 6(1)(d) | extraction + format |
| R5 | MRP in prescribed wording: "Maximum Retail Price Rs. X (inclusive of all taxes)" — bare "MRP 20" is a violation | 2(m), 6(1)(e) | extraction + format |
| R6 | Consumer care details: name, phone, email | 6(2) | extraction |
| R7 | Declarations in Hindi (Devanagari) or English | 9(4) | OCR script detection |
| R8 | Minimum numeral height for MRP/quantity numerals vs principal-display-panel area class (A < 50 cm² → ≥1.0 mm normal / ≥1.5 mm molded; 50 < A < 100 → ≥1.5 / ≥3.0; 100 < A < 500 → ≥2.5 / ≥4.0; 500 < A < 2500 → ≥4.0 / ≥6.0; 2500 < A → ≥6.0 / ≥6.0) | 7(2) + Table-I as substituted by GSR 629(E), w.e.f. 1.1.2018 | geometry: PDP area = measured width × height from the same photo calibration (Rule 7(4)(a)) or exact page dimensions on PDFs; exact mm on vector PDFs; calibrated mm on photos; NA with NO_SCALE_REFERENCE when uncalibrated |
| R9 | Clear space around quantity declaration (≥1× numeral height above/below, ≥2× left/right) | 8 | geometry |
| R10 | MRP/quantity numerals contrast conspicuously with background | 9(1)(b) | pixel contrast analysis |
| R11 | No misleading quantity qualifiers ("minimum", "approx", "average", "when packed") | 12(6) | extraction + word-list |

- [LOCKED] Every check returns **pass / fail / NA** (imported package, exempt category, unreadable). Blindly applying every check to every label is wrong and looks dumb.
- [LOCKED] **Light exemption layer** from Rule 26 — detectable exemptions only (packs <10 g/ml fully exempt; >25 kg/l → NEEDS_REVIEW); undetectable categories (institutional/industrial, DPCO, hotel food, agricultural >50 kg, thread coils, loose garments) are covered by the report footer, never the engine. Full exemption matrix = roadmap.

## 4. LLM boundary — the trust architecture

- [LOCKED] **THE CORE PRINCIPLE — model-independent correctness:** the model's quality may change **coverage** (how many fields get extracted), never **correctness** (whether a given verdict is right). Every verdict must trace to deterministic verification (crop-verify OCR on pixels, or PDF text-layer) — never to raw model output. A weak model yields more `NA`/`NEEDS_REVIEW`, never more wrong answers. The system itself detects incomplete extraction and reports it honestly (e.g., "found 5 of 7 declarations"), and the benchmark reports accuracy and coverage as separate numbers.

- [LOCKED] Principle: **the LLM reads the label; code judges it. The judge never hallucinates.**
- [LOCKED] LLM (Amazon Bedrock) is used for exactly ONE job: extraction — fields + bounding boxes from the photo/PDF. All 11 verdicts, geometry, reports = pure Python.
- [LOCKED] Verification gauntlet (full spec: ENGINEERING.md Feature 1): every claim passes deterministic gates — box sanity, text sanity, parsed↔raw consistency, crop-verify (OCR match inside the claimed box), keyword-anchor check (box must contain the field's keyword, e.g. an "MRP" claim needs an OCR-detected MRP anchor in that box), confidence gate. Verifier = Tesseract word-index (deterministic; PDFs use the exact text layer instead).
- [LOCKED] **Missing vs unreadable:** a mandatory declaration that is confidently absent from a readable label (readability score from the OCR word index passes, field null everywhere) is reported as **FAIL — "not found on label"** (a real violation, most common case: missing MRP), never swallowed as NA. Only genuinely undeterminable cases become NA. Every NA/NEEDS_REVIEW carries a reason code (`NOT_PRINTED`, `UNREADABLE_IMAGE`, `VERIFY_FAILED`, `LOW_CONFIDENCE`, `UNSUPPORTED_LANGUAGE`, `NO_SCALE_REFERENCE`, `DEPENDENCY_UNAVAILABLE`, `NA_EXEMPT`, `EXTRACTION_MISS`) + human-readable message + suggested action. Partial report principle: a failed gate on one field never fails the scan; only unparseable garbage does. Reports always state "found X of 7 declarations".
- [LOCKED] **Extraction cache:** the same label never hits Bedrock twice. Dev iterations on rule engine/UI run on cached JSON. This is also the cost control.
- [LOCKED] Model strategy: **Haiku-first, Sonnet fallback** for low-confidence reads. Model sits behind one interface so it's swappable.
- [LOCKED] Cost reality: one extraction call ≈ well under $0.01 (Haiku); the 100-label benchmark ≈ $1–2. $100 credits are more than enough.

## 5. AWS architecture — 4 services, nothing else

- [LOCKED] **S3** — 3 buckets: `labelcheck-uploads` (private, label photos/PDFs in), `labelcheck-outputs` (public-read: annotated images + generated reports), `labelcheck-web` (static React build). One bucket with mixed permissions is how leaks happen.
- [LOCKED] **Lambda** — ONE function, invoked two ways: (a) Function URL for the API (routed by path), (b) S3 `ObjectCreated` trigger for processing. Function URL over API Gateway = deliberate cost decision for the Ship It pitch.
- [LOCKED] **DynamoDB** — single `scans` table, PK `scan_id`, GSIs for history/status and brand search. One table + 2 GSIs beats a relational schema for a 4-day build.
- [LOCKED] **Bedrock** — extraction only (see section 4).
- [LOCKED] NO API Gateway, NO EventBridge/SNS/queues, NO Cognito in MVP (stretch only). If a service isn't earning its place in this pipeline, it's not in.
- [LOCKED] Region: **ap-south-1 (Mumbai)** for everything.
- [LOCKED] Presigned uploads: photo goes browser → S3 directly; Lambda never proxies bytes.

### Flow (5 steps)

1. `POST /upload` → presigned PUT URL + PENDING record
2. Browser PUTs photo to S3 (uploads bucket)
3. S3 event → Lambda processing pipeline: preprocess → Bedrock extract → validate (schema + crop-verify) → rule engine (11 checks + exemptions) → generate annotated image + reports
4. Results written: record to DynamoDB, artifacts to outputs bucket
5. Frontend polls `GET /scans/{id}` until status leaves PROCESSING; renders report card

### Scan lifecycle

`PENDING → PROCESSING → DONE | NEEDS_REVIEW | FAILED` — degradation is a feature: an unreadable field is flagged for rescanning, never guessed.

## 6. Data contracts

- [LOCKED] Two frozen JSON shapes (full schemas to live in `CONTRACTS.md`, repo root):
  1. **Extraction JSON** — fields + boxes + language + per-field confidence
  2. **Scan record** — scan_id, status, ts, summary (pass/fail/na counts), results[] with rule_id, name, citation, status, evidence, fix, box, measurement (geometry results only — approved 2026-09-17)
- [LOCKED] API surface: `POST /upload`, `GET /scans/{id}`, `GET /scans` (search/pagination), `GET /stats`, `GET /reports/{id}` (pdf/json/csv).
- [LOCKED] Contracts are frozen before parallel frontend/backend work starts; changing a contract = team decision + PROGRESS.md entry.

## 7. Team & workflow

- [LOCKED] Team of 4: 2 backend, 2 frontend. Nobody has used S3/Lambda/DynamoDB before — the plan accounts for it.
- [LOCKED] ONE project AWS account (owner: whoever created it). 4 separate IAM users, one per member — no shared keys. Keys never in the repo or group chats; they live in `~/.aws/credentials`.
- [LOCKED] Deploy discipline: ONE person owns Lambda deploys. Two people deploying the same function = overwrite war.
- [LOCKED] Rule engine is pure Python, tested locally without AWS. Frontend builds against mocked contracts. AWS-unfamiliarity never blocks anyone.
- [LOCKED] During dev, members may use their own accounts' credits for experiments; final stack lives on the project account.

### Build risks with pre-agreed fallbacks

- [LOCKED] Font size from photos: **calibrated** measurement — plain-background auto-segmentation (Otsu + minAreaRect + rectangularity/shadow gate) + optional user-supplied label width in mm; exact millimetres on vector PDFs. Absolute-size measurement from *uncalibrated* photos remains out of scope (physically impossible). Pre-agreed shrink if calibration proves flaky during the build: photo R8 → NA with NO_SCALE_REFERENCE; all other checks unaffected.
- [LOCKED] Geometry checks (R8–R10) are the hardest technical piece — if they cannot be made solid, they degrade to NA with reason codes (photo R8 → NO_SCALE_REFERENCE shrink); never silently dropped without a PROGRESS.md entry.
- [LOCKED] Bedrock prompt tuning may eat time — the extraction cache keeps iterations cheap.
- [LOCKED] Video priority: benchmark accuracy numbers, a polished report-card UI, and visible AWS fit are the three things the demo video must land.

## 8. Build tooling (AI agents)

- [LOCKED] IDE: **Antigravity**. Coding: **Gemini 3.1 Pro**. Debugging + user-perspective testing: **Nex 2.5 Pro**. Both get named in the hackathon writeup.
- [LOCKED] Strategy (because the models are not Claude-level, the documents carry the intelligence): precise specs, TDD with fixtures, one task = one file + its tests, PROGRESS.md updated after every task, human reviews every task before merge.
- [LOCKED] Repo doc structure (updated 2026-09-18 — monorepo layout, owner-directed; decision log same date): `AGENTS.md` (agent constitution + verify commands), `PROGRESS.md` (live state + decision log), `TASKS.md` (queue), `CONTRACTS.md` (repo root — frozen schemas, the ONLY shared document), `backend/docs/ENGINEERING.md` (proven designs, Features 1–10), `backend/docs/ARCHITECTURE.md` (text version — NOT the HTML), `backend/docs/CHECKS.md` (exact spec per check: citation, pass/fail logic, edge cases, examples), `backend/fixtures/` (golden extraction JSONs = TDD answer key).
- [LOCKED] **Doc scoping — backend vs frontend:** `backend/docs/ARCHITECTURE.md`, `backend/docs/ENGINEERING.md` and `backend/docs/CHECKS.md` are BACKEND build documents — backend agents only; they describe the server system and must never lead to frontend code. **`CONTRACTS.md` (repo root) is the ONLY shared document** — the frontend track (2 members) builds entirely against it, with its own UI-focused doc if needed.
- [LOCKED] **Proof-first rule:** no feature or stage gets coded before its approach is written down AND mathematically justified (error sources, bounds, cost/latency budget) in the docs. Agents receive a proven approach + implementation direction — they translate designs into code; they never make design decisions. Design correctness is proven by the math; implementation correctness is enforced by fixtures/TDD.

## 9. Open items (decide later, in order)

1. Final product name
2. Which member owns Lambda deploys; IAM usernames
3. Exact Bedrock inference profile IDs (wire during integration)

---

## Decision log

| Date | Decision |
|---|---|
| 2026-09-16 | Initial lock: problem statement (SIH26034), 3 core features, 11 checks, LLM boundary, 4 AWS services, contracts, team split, AI tooling strategy, repo doc structure |
| 2026-09-16 | Added official judging criteria: 5 criteria incl. Learning (scores points); writeup must include what we learned; demo video must show where AWS fits |
| 2026-09-16 | LOCKED the core architecture principle: model-independent correctness — model quality affects coverage only, never verdict correctness; accuracy and coverage reported separately |
| 2026-09-16 | Doc scoping: ARCHITECTURE/ENGINEERING/CHECKS are backend-only build docs; CONTRACTS.md is the only shared doc. Proof-first rule locked: math before code, agents translate proven designs only |
| 2026-09-16 | Feature 1 (extraction verification gauntlet) proven and locked into ENGINEERING.md: 6 deterministic gates + Tesseract word-index; theorem P(wrong verdict) ≤ ε_ocr independent of LLM; missing-vs-unreadable decision table with reason codes |
| 2026-09-17 | Feature 2 (geometry engine R8–R10) proven and locked into ENGINEERING.md: R9/R10 scale-free on any photo; R8 = exact mm on PDFs, calibrated mm on photos (Otsu segmentation + optional user label width, minAreaRect, rectangularity/shadow gate, tilt absorbed in 3σ bands, implausibility sanity check), NA with NO_SCALE_REFERENCE otherwise; photo path scoped to flat packets + cartons (planar math); contrast via WCAG formula @ 3:1 (interpretive threshold, fixture-calibrated); R10 embossed proviso → NA; optional label_width_mm added to upload contract |
| 2026-09-17 | Feature 3 (rule engine framework + R1–R7, R11) proven and locked: field-status pre-resolution (VERIFIED/ABSENT/UNREADABLE/NEEDS_REVIEW/NA_EXEMPT), pure-function checks, dependency declarations with new reason code DEPENDENCY_UNAVAILABLE (7th), per-check decision tables, interpretation registry (4 documented calls — ambiguity always → NEEDS_REVIEW, never wrong FAIL), sticker-MRP multiple-instance rule, R11 scoped to quantity raw only, classification-rate bar ≥85% definitive verdicts on clean fixtures; "1500 g" stays PASS (benchmark watch-list) |
| 2026-09-17 | Feature 4 (exemption layer + NA semantics) proven and locked: inverted-risk principle — an uncertain exemption degrades to NEEDS_REVIEW, never a wrong exemption (a false exemption = false PASS). Detectable exemptions only: ≤10 g/ml (Rule 26(a) — requires VERIFIED quantity + VERIFIED non-tobacco generic_name; tobacco proviso comes from amendment, base-text 10–20 g proviso withdrawn wef 01.07.2012; pieces never exempt per "sold by weight or measure" qualifier) and >25 kg/l (Rule 3(a) → NEEDS_REVIEW, cement/fertilizer exception undetectable). Undetectable exemptions (institutional/industrial, DPCO, hotel food, agricultural >50 kg, thread coils, loose garments) documented + report footer. Exempt scans = DONE + all checks NA_EXEMPT + separate summary count; CONTRACTS.md gained additive `exemption` object. Gazette text re-verified for Rule 26 and Rule 3 during self-challenge |
| 2026-09-17 | Feature 5 (ingestion path) proven and locked into ENGINEERING.md: presigned PUT (ContentType-pinned, 900 s) + DynamoDB conditional claim (atomic PENDING→PROCESSING test-and-set) → exactly-once pipeline execution under at-least-once S3 delivery and Lambda retries; phantom-record trap avoided (condition `status = :pending`, not `attribute_not_exists`); stale-state guards — STALE_PROCESSING reaper (5 min, timestamp-guarded), UPLOAD_TIMEOUT (960 s + HeadObject 404), EVENT_NOT_RECEIVED (rare event loss); size cap 20 MB at claim time from the event's size field; ConsistentRead on GET /scans/{id}. Approved additive semantics: direct PENDING→FAILED transition (upload-timeout family) — CONTRACTS.md text, statuses and shapes unchanged |
| 2026-09-17 | Feature 6 (report generator) proven and locked into ENGINEERING.md: annotated image via PIL (red/green/amber, proportional stroke, grouped identical boxes, legend banner — boxes drawn only on the canonical processed image, one coordinate space), PDF via reportlab invariant mode (page 1 = annotated image, report-card table, "found X of 7 declarations", exemption banner, non-exempt-retail footer, non-Latin → placeholder), CSV RFC 4180 + UTF-8 BOM, JSON = record serialized; render-fidelity + byte-determinism theorems; artifacts generated in memory then 5 PUTs, then the single terminal write (Feature 5 ordering). Two approved additive CONTRACTS.md changes: artifacts.display_image (public resized original, max edge 1600 px, EXIF-stripped — enables UI original/annotated toggle + interactive box overlay) and summary.found_declarations (VERIFIED count of the 7 declaration fields). Scope calls: multi-page PDFs → first page only in MVP (roadmap); artifact failure after one retry → scan FAILED |
| 2026-09-17 | Feature 7 (API + storage) proven and locked into ENGINEERING.md: GSI-1 (PK const, SK created_at#scan_id) for newest-first paginated history; GSI-2 (SK brand_key#…) brand-prefix fast path + capped-loop Scan contains(brand_key | product_key) fallback — true fuzzy without a search service; rule_id filter via write-time failed_rules String Set (attribute omitted when empty); stats = on-demand aggregation with 60 s warm cache (no counters → no drift class, no F5 interplay; total_scans = all records, overall/by_rule = terminal results only); reports served by 302 redirect to public S3 URLs; internal attributes stripped by whitelist serializer. Read-purity, pagination-completeness and stats-non-drift theorems; storage scale ceiling (≤ a few thousand scans) documented. CONTRACTS.md unchanged |
| 2026-09-17 | Feature 8 (benchmark harness) proven and locked into ENGINEERING.md: ground truth = per-label JSON (per-rule verdicts + 7 printed field values + physical measurements with uncertainty) in the CONTRACTS §5 fixture shape — benchmark labels double as regression fixtures; metrics defined exactly (accuracy over definitive-on-definitive, coverage separate, false-definitive counter, ε_ocr from field-value contradictions, exempt cohort as counts); labeling authority = ENGINEERING decision tables, boundary stated (system-vs-spec, not spec-vs-law); R8 boundary-truth exclusion (±0.3 mm); 2-labeler + third-opinion adjudication; stratified sampling minimums (~10% Hindi, ≥10 R5 violations, ≥5 exempt, ≥10 uncalibrated, ≥5 PDFs); flow: deployed-stack initial pass → harvested inline extractions → offline deterministic replay; stability sub-run (20 labels, BENCHMARK_SKIP_CACHE default-off); one live 10-label validation for Ship It numbers; Clopper-Pearson CIs — zero-wrong reported as 0/N + upper bound, actual N always stated. CONTRACTS.md unchanged |
| 2026-09-17 | Documentation consistency pass (owner-approved, mechanical syncs only — no design decisions made or changed): stale text aligned to already-logged decisions. Reason-code lists now 8 codes everywhere (NA_EXEMPT added — F4 log). §3 exemption-layer scope matches F4 (loose garments = report footer, not engine). §8 doc structure lists docs/ENGINEERING.md. CONTRACTS.md synced to logged decisions: GET /reports → 302 (F7 log); validation gate 5 → dependent checks NA with DEPENDENCY_UNAVAILABLE (F3 log); PENDING→FAILED note (F5 log); 20 MB upload cap (F5); GSI description (F7); scan error-code enum (F5/F6); `exemption` key added to the example record (every-key-exists convention); `last_key` = opaque base64 cursor (F7); banner counts include NA (F6 6.9 item 11). TASKS.md: 8 docs not 7; T0.3 citations (F6 6.8 item 7, F7 7.9 item 10); dependency fixes (T2.6 before T2.2; T3.7 before T3.3–T3.6; T4.3 needs T4.2; T5.7 needs T2.7 + T3.8); T2.6 contrast band 2.5–3.5; 'F8 6' → 'F8 8.6'. CHECKS.md header + TASKS H2 labeling authority aligned to the F8 log entry. Open design items deliberately NOT touched (require team decisions + proofs): extraction feature spec, preprocess module, extraction-cache store, field-status bridge, ABSENT definition, σ base, R8 200 g boundary, scan-level NEEDS_REVIEW rule, R1 name semantics, R7 threshold, R5 multi-MRP mechanism, embossed detection, minAreaRect approach, measurement schema, brand_guess producer, CONTRACTS §5 ground-truth shape, anchors.config initial content, uploads CORS origin, unanchored-verified tag placement |
| 2026-09-17 | Design decision session (owner-approved) — 11 decisions + 2 approach calls locked: D1 σ = 0.05 × measured H (F2 examples corrected: H = 2.5 → PASS). D2 pack-class boundary: exactly 200 g/ml = ≤ 200 class (1 mm normal / 2 mm embossed); the > 200 row starts above 200. D3 scan-level rule: terminal NEEDS_REVIEW iff any result is NEEDS_REVIEW or the exemption layer is uncertain, else DONE. D4 R1: manufacturer_name ABSENT on a readable label → FAIL. D5 brand_guess = optional 8th extraction field, NOT a declaration (gauntlet-exempt, box nullable, never counted in found_declarations) powering product.brand_guess. D6 summary.exempt = NA_EXEMPT result count (additive). D7 R7 predominantly = > 50 % of script-bearing characters per declaration (INTERPRETATION #5). D8 multiple-MRP detection = deterministic word-index anchor sweep, ≥ 2 distinct values. D9 field-status bridge table locked (7 rows) + ABSENT = anchor-qualified + new reason code EXTRACTION_MISS (9th). D10 G4 normalization = casefold + NFKC + strip punctuation + collapse whitespace, numerals exact (same family as ε_ocr). D11 extraction cache = S3 cache/ prefix in the uploads bucket, key = ETag, IAM gains uploads write. Approach calls: extraction = single Haiku call with structured output (7 fields + brand_guess), Sonnet retry once on G0 schema fail or ≥ 2 fields with confidence < 0.60, Bedrock failure → FAILED(EXTRACTION_FAILED); embossed detection = same-ink signature (near-zero chroma distance + low contrast → NA), ambiguous → NEEDS_REVIEW, fixture-calibrated. CONTRACTS additive changes approved: brand_guess field, summary.exempt, results[].measurement schema (R8: measured_mm / sigma_mm / required_mm / pack_class / method), error codes + EXTRACTION_FAILED; DECISIONS §6 results[] gains measurement. Still open (design pass): Feature 9 extraction spec, preprocess module, minAreaRect approach, embossed detector spec, CONTRACTS §5 ground-truth shape, anchors.config content |
| 2026-09-18 | Design + legal-correction session (owner-approved) — 12 decisions locked: D12 R8 legal correction: Rule 7(2) Table-I as substituted by GSR 629(E), w.e.f. 1.1.2018 is AREA-based (PDP cm² classes: <50 → 1.0/1.5; 50–100 → 1.5/3.0; 100–500 → 2.5/4.0; 500–2500 → 4.0/6.0; >2500 → 6.0/6.0 mm) — the pre-2018 weight/volume table is superseded law (the docs had codified it from the unamended 2011 gazette PDF); the 2026-09-17 200 g boundary decision (D2) is superseded with it. Class key = measured PDP area (photo: same calibration, Rule 7(4)(a); PDF: exact page dims); class-interval rule folds area uncertainty into the 3σ verdict (FAIL only vs R_min, PASS only vs R_max); INTERPRETATION #6 embossed → molded column; #7 exact-boundary A → less strict class; watch note: A<50 molded 1.5 (amendment gazette) vs 2.0 (some compilations) — 1.5 codified, config value; scope stays MRP + quantity numerals (letters + 7(3) width proviso = roadmap). D13 Feature 9 extraction module: one Haiku Converse call with toolConfig schema enforcement, G0 jsonschema, Sonnet retry on G0 fail or ≥2 fields <0.60, EXTRACTION_FAILED, ETag cache, model-ID defaults. D14 Feature 10 preprocess: EXIF transpose / PDF page 1 @ 200 DPI (PyMuPDF; first-page-only per the F6 lock). D15 minAreaRect = PCA extents (pure numpy). D16 embossed/molded detector: ΔE CIE76 + WCAG bands (ΔE<10 ∧ C<2.5 relief; ΔE≥15 ∧ C<2.5 pale print; else NEEDS_REVIEW). D17 CONTRACTS §5 fixture shape locked. D18 anchors.config + taxes-variant initial content locked. D19 TASKS rewiring: T1.8 extraction, T1.9 preprocess, PyMuPDF layer, H5 SIH PPT + H6 demo video + H7 writeup, feature count 8→10, AGENTS reason codes 8→9. D20 R9 PDF ink-coverage via pdfplumber objects. D21 unanchored-verified tag = static display hint (CONTRACTS note). D22 CORS origin placeholder + model-ID defaults. D23 90% accuracy target stated in the F8 report, never a gate. Legal sources: GSR 629(E) amendment gazette (23.06.2017, w.e.f. 1.1.2018); Maharashtra compiled LMPC Rules (as amended up to GSR 629(E)); PIB release ID 1497129 (25.07.2017) |
| 2026-09-18 | Repo layout (owner-directed) — monorepo with `frontend/` + `backend/`; `CONTRACTS.md` promoted to repo root (the ONLY shared document — the FE track builds against it); backend-only docs moved to `backend/docs/` (ENGINEERING, CHECKS, ARCHITECTURE); §8 doc-structure + scoping paths updated accordingly; 13 path references swept to repo-root-relative paths across AGENTS/PROGRESS/TASKS/backend docs; TASKS-implied folder skeleton created (src/gauntlet, src/geometry, src/rules, src/extraction, src/preprocess, src/ingestion, src/reports, src/api, config, fixtures, benchmark, infra, lambda); .gitignore + README stub (T0.1). Repo created inside the event window (17–20 Sept). `fixtures/` path in §8 now `backend/fixtures/` |
