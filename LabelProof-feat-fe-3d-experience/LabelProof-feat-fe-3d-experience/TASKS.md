# TASKS.md -- The Queue

**Rule:** one task = one file + its tests (DECISIONS.md 8). Take the next unblocked task; update PROGRESS.md after every task; a human reviews before merge. Every backend task cites its ENGINEERING.md feature section -- that section is the spec; the acceptance criteria are the test list.

**Assignments:** unassigned until the team decides (DECISIONS.md 9 open item: deploy owner + IAM usernames).

**Legend:** P = phase. Deps = task IDs that must land first. FE = frontend track (builds against CONTRACTS.md ONLY). H = human task (no agent).

---

## Phase 0 -- Repo + Infra (day 1, parallel with Phase 1)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T0.1 H | Repo init (17 Sept only -- history must match the event window), branch main + protect, .gitignore, README stub, copy the 8 docs in | repo root | - | DECISIONS 0 |
| T0.2 H | AWS account setup: 4 IAM users (one per member, no shared keys), credentials in ~/.aws/credentials only | infra/ | T0.1 | DECISIONS 7 |
| T0.3 | 3 S3 buckets: labelcheck-uploads (private, CORS JSON for browser PUT), labelcheck-outputs (public-read bucket policy), labelcheck-web (static) -- verbatim infra configs from ENGINEERING F5 5.8 item 8 (uploads CORS + trigger), F6 6.8 item 7 (outputs public-read policy), F7 7.9 item 10 (outputs CORS) | infra/buckets/ + scripts | T0.2 | F5, F6, F7 |
| T0.4 | DynamoDB `scans` table: PK scan_id + GSI-1 (PK const SCAN, SK created_at#scan_id) + GSI-2 (PK const BRAND, SK brand_key#created_at#scan_id) -- F7 7.9 item 10 | infra/dynamodb/ | T0.2 | F7 |
| T0.5 | Lambda skeleton: ONE function, Function URL + S3 ObjectCreated trigger (prefix uploads/), invocation-type branching stub; env vars (table, buckets, region) | lambda/handler.py + infra/lambda/ | T0.3, T0.4 | F5 5.8 items 9 |
| T0.6 | Lambda layers: Tesseract (+ eng/hin data), reportlab + Pillow + numpy + scipy + PyMuPDF -- version-pinned (benchmark determinism depends on it) | infra/layers/ | T0.5 | F1 1.9, F6, F8, F10 |
| T0.7 | Bedrock access check: Haiku + Sonnet model IDs resolve in ap-south-1 (defaults: anthropic.claude-3-5-haiku-20241022-v1:0 / anthropic.claude-sonnet-4-20250514-v1:0, env-driven; wire the exact inference profile IDs -- DECISIONS 9 open item) | infra/bedrock/ | T0.2 | DECISIONS 9, F9 |

## Phase 1 -- Feature 1: verification gauntlet (pure Python, no AWS needed)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T1.1 | Word-index builder: build_word_index(image) -> [{word, box, confidence}] (Tesseract; pdfplumber for PDFs) + tests | src/gauntlet/word_index.py | T0.1 | F1 1.9 item 1 |
| T1.2 | Gates G1-G6: six independent pure functions, separate files (G1 box sanity, G2 raw non-empty, G3 parsed<->raw, G4 crop-verify edit-distance-0, G5 anchor, G6 confidence) + tests | src/gauntlet/gates/g1..g6.py | T1.1 | F1 1.9 item 2 |
| T1.3 | anchors.config (field -> keyword regexes) + loader + tests | config/anchors.config | T1.2 | F1 1.9 item 3 |
| T1.4 | reasons.config (code -> message + suggested_action) + result mapper (the decision-table switch) + tests | config/reasons.config, src/gauntlet/mapper.py | T1.2 | F1 1.9 items 4, 6 |
| T1.5 | Readability score: pure function over word index, thresholds in config + tests | src/gauntlet/readability.py | T1.1 | F1 1.9 item 5 |
| T1.6 | Extraction cache interface: ETag-keyed get/put (S3 `cache/` prefix in the uploads bucket, key = ETag — decision log 2026-09-17) + tests | src/gauntlet/cache.py | T1.1 | F1 1.9 item 7 |
| T1.7 | F1 acceptance fixtures: 7 criteria of F1 1.10 (hallucination x10, misread x10, wrong-attribution x10, missing-declaration x10, poor-quality x10, clean x20, reason-code completeness) | fixtures/f1/ | T1.2-T1.5 | F1 1.10 |
| T1.8 | Bedrock extraction client: Converse API + toolConfig (schema-enforced), verbatim prompt file, G0 jsonschema validation, Sonnet fallback (G0 fail OR >=2 fields <0.60), EXTRACTION_FAILED on double failure, ETag cache wiring, vision downscale + box scale-back + tests | src/extraction/client.py, src/extraction/schema.py, src/extraction/fallback.py | T1.1, T0.7 | F9 |
| T1.9 | preprocess(raw_bytes, content_type) -> canonical image: EXIF transpose (photos, original resolution), PDF page 1 @ 200 DPI (PyMuPDF) + tests | src/preprocess/canonical.py | T0.6 | F10 |

## Phase 2 -- Feature 2: geometry engine (pure Python)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T2.1 | measure_numeral_height(image, box) -> median digit height px (connected components) + tests | src/geometry/measure.py | T1.7 | F2 2.7 item 1 |
| T2.2 | calibrate_photo(image, label_width_mm) -> scale + sigma + PDP area OR NA reason (Otsu, numpy minAreaRect, rectangularity >= 0.80, tilt, sanity 0.5-4.0 mm) + tests | src/geometry/calibrate.py | T2.1, T2.6 | F2 2.7 item 2 |
| T2.3 | check_r8 (3-sigma band + class-interval rule; Rule 7 Table-I area classes [GSR 629(E) 2018] + embossed/molded detector thresholds in thresholds.config) + tests | src/geometry/check_r8.py | T2.2 | F2 2.7 item 3 |
| T2.4 | check_r9 (exclusion zone: word-index + ink coverage) + tests | src/geometry/check_r9.py | T1.7 | F2 2.7 item 4 |
| T2.5 | check_r10 (WCAG contrast, digit pixels exact; embossed -> NA) + tests | src/geometry/check_r10.py | T1.7 | F2 2.7 item 5 |
| T2.6 | thresholds.config (contrast bands 2.5–3.5, rectangularity, sanity bounds, resolution floor, Rule 7 table) + tests | config/thresholds.config | T2.1 | F2 2.7 item 6 |
| T2.7 | F2 acceptance fixtures: 10 criteria of F2 2.8 (1.0mm FAIL, 2.0mm PASS, boundary + class-boundary NEEDS_REVIEW, no-width NA, shadow NA, 2x-width sanity, yellow-on-white, same-ink relief vs pale print, PDF exact, two-run identity) | fixtures/f2/ | T2.3-T2.5 | F2 2.8 |

## Phase 3 -- Feature 3: rule engine framework + checks (pure Python)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T3.1 | resolve_field_statuses(gauntlet_output, readability, exemptions) -> field_status map + tests | src/rules/statuses.py | T1.7 | F3 3.7 item 1 |
| T3.2 | run_checks(context) framework: registry, requires declarations, DEPENDENCY_UNAVAILABLE short-circuit; no check reads the LLM's confidence directly -- verdicts trace to field_status + patterns only + tests | src/rules/engine.py | T3.1 | F3 3.7 items 2, 3, 5 |
| T3.3 | Checks R1 + R2 (address two defenses + region analysis; presence) + tests + fixtures | src/rules/checks/r1.py, r2.py | T3.2, T3.7 | F3 3.3 |
| T3.4 | Checks R3 + R4 (unit decision table; date whitelist) + tests + fixtures | src/rules/checks/r3.py, r4.py | T3.2, T3.7 | F3 3.3 |
| T3.5 | Checks R5 + R6 (wording tiers + sticker rule; contactable) + tests + fixtures | src/rules/checks/r5.py, r6.py | T3.2, T3.7 | F3 3.3 |
| T3.6 | Checks R7 + R11 (script composition; qualifier scope) + tests + fixtures | src/rules/checks/r7.py, r11.py | T3.2, T3.7 | F3 3.3 |
| T3.7 | patterns.config (MRP tiers, date formats, PIN regex, state list, qualifiers, Third Schedule 26 items, fix messages) + tests | config/patterns.config | T3.2 | F3 3.7 item 4 |
| T3.8 | F3 acceptance fixtures: 7 criteria of F3 3.8 (20 status fixtures, classification bar >= 85%, every decision-table row, R11 scoping, dependency NA, fix/reason completeness, determinism) | fixtures/f3/ | T3.3-T3.6 | F3 3.8 |

## Phase 4 -- Feature 4: exemption layer (pure Python)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T4.1 | evaluate_exemptions(gauntlet_output) -> EXEMPT / NEEDS_REVIEW(reason) / NONE; unit conversion reuses the R8/R9 table (never a second one) + tests | src/rules/exemptions.py | T3.1 | F4 4.8 items 1, 2, 4 |
| T4.2 | tobacco.config + case-insensitive word-boundary matcher + tests | config/tobacco.config | T4.1 | F4 4.8 item 3 |
| T4.3 | F4 acceptance fixtures: 8 criteria of F4 4.9 (sachet EXEMPT, gutkha NEEDS_REVIEW, unverified commodity, 30 kg, pcs, 10.5/11 g boundary, separate summary count, determinism) | fixtures/f4/ | T4.1, T4.2 | F4 4.9 |

## Phase 5 -- Feature 5: ingestion (AWS integration)

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T5.1 | generate_scan_id() (charset from ingestion.config, ^SC-[A-HJ-NP-Z2-9]{6}$) + create_pending_record (attribute_not_exists, collision regenerate max 3) + tests | src/ingestion/upload.py | T0.5 | F5 5.8 items 1, 2 |
| T5.2 | presign_upload(key, content_type) -- 900 s, ContentType signed + tests | src/ingestion/presign.py | T5.1 | F5 5.8 item 3 |
| T5.3 | claim_scan(scan_id, size_bytes) -- THE conditional update, returns claimed: bool, never raises on condition failure; scan_id parsed from the S3 key + tests | src/ingestion/claim.py | T5.1 | F5 5.8 item 4 |
| T5.4 | mark_terminal(scan_id, status, error) -- conditional write guarded on status = :processing + tests | src/ingestion/terminal.py | T5.3 | F5 5.8 item 5 |
| T5.5 | reap_stale_processing / reap_stale_pending (timestamp + status conditions; HeadObject 404 branch) + tests | src/ingestion/reapers.py | T5.4 | F5 5.8 item 6 |
| T5.6 | ingestion.config (content types, 20 MB cap, 5 min / 960 s stale, 900 s presign, charset) + tests | config/ingestion.config | T5.1 | F5 5.8 item 7 |
| T5.7 | Wire POST /upload route into handler + event path (size gate -> claim -> pipeline handoff -> try/finally terminal) + integration test on AWS | lambda/handler.py | T2.7, T3.8, T4.3, T5.2-T5.5, T0.7 | F5 5.8 items 9, 10 |
| T5.8 | F5 acceptance fixtures: 11 criteria of F5 5.9 (duplicate seq, concurrent claims, phantom-record, late event, oversized, exception->FAILED, reaper rows, upload-timeout rows, 400 validations, 1000 scan_ids, determinism) | fixtures/f5/ | T5.7 | F5 5.9 |

## Phase 6 -- Feature 6: report generator

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T6.1 | render_annotated(canonical_image, results, config) -- box validation, grouping, colors, banner + tests | src/reports/annotate.py | T5.8 | F6 6.8 item 1 |
| T6.2 | render_display_image (max edge 1600, EXIF stripped) + tests | src/reports/display.py | T5.8 | F6 6.8 item 2 |
| T6.3 | sanitize_pdf_text (Latin-safe placeholder) + build_pdf_report (reportlab invariant mode, page 1 image, table, found X of 7, exemption banner, footer) -- no clock reads, timestamps come from record fields only + tests | src/reports/pdf.py | T5.8 | F6 6.8 items 3, 5, 9 |
| T6.4 | build_csv_report (RFC 4180 + UTF-8 BOM) + record serializer + tests | src/reports/csv.py | T5.8 | F6 6.8 item 4 |
| T6.5 | reports.config (colors, stroke scale, banner format, JPEG quality, max edge, DPI, margins, retry) + found_declarations computation from field_status + tests | config/reports.config, src/reports/summary.py | T6.1 | F6 6.8 items 6, 10 |
| T6.6 | Wire into pipeline: generate all 5 artifacts in memory -> 5 PUTs -> single terminal write; retry once then FAILED(INTERNAL) + integration test | lambda/handler.py | T6.1-T6.5 | F6 6.8 items 8, 9 |
| T6.7 | F6 acceptance fixtures: 12 criteria of F6 6.9 (box-color match, out-of-bounds skip, grouped boxes, byte-identical reruns, Devanagari placeholder, exempt report, artifact-failure FAILED, display resize, found 5 of 7, multi-page first-only, banner = summary counts, determinism) | fixtures/f6/ | T6.6 | F6 6.9 |

## Phase 7 -- Feature 7: API + storage

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T7.1 | router.py -- (method, path) dispatch, trailing-slash strip, 404/405 in contract error format + tests | src/api/router.py | T5.7 | F7 7.9 item 1 |
| T7.2 | list_scans -- GSI-1 query newest-first + status/rule_id filters + cursor encode/decode (400 on garbage) + tests (moto) | src/api/list_scans.py | T7.1 | F7 7.9 item 2 |
| T7.3 | search_scans -- GSI-2 prefix leg + capped-loop Scan fallback (limit = RESULT count) + AND composition + tests (moto) | src/api/search.py | T7.2 | F7 7.9 item 3 |
| T7.4 | get_scan -- consistent GetItem + reaper wiring (F5 5.4 functions) + tests | src/api/get_scan.py | T5.5 | F7 7.9 item 4 |
| T7.5 | get_stats -- Scan + aggregate (total = all records; overall/by_rule = terminal results), 60 s warm cache + tests | src/api/stats.py | T7.2 | F7 7.9 item 5 |
| T7.6 | redirect_report -- status check -> 302 Location + tests | src/api/reports.py | T6.6 | F7 7.9 item 6 |
| T7.7 | serialize (whitelist: internal keys never in responses) + normalize_key (one function, write + query) + tests | src/api/serialize.py | T7.2 | F7 7.9 items 7, 8 |
| T7.8 | api.config (cache TTL, fallback page cap 10, pagination max 100, GSI constants) + F7 acceptance fixtures: 13 criteria of F7 7.10 (moto-backed) | config/api.config, fixtures/f7/ | T7.2-T7.7 | F7 7.9 items 9, F7 7.10 |

## Phase 8 -- Feature 8: benchmark harness

| ID | Task | Files | Deps | Spec ref |
|---|---|---|---|---|
| T8.1 | collect_driver.py -- uploads label set through the deployed API, polls, harvests records + tests | benchmark/collect_driver.py | T5.7, T7.4 | F8 8.10 item 1 |
| T8.2 | run.py -- offline replay: harvested extraction -> gauntlet -> rule engine -> results (pinned versions, zero network) + tests | benchmark/run.py | T8.1 | F8 8.10 item 2 |
| T8.3 | score.py -- pure metric function (definitions of F8 8.3 as one switch) + tests | benchmark/score.py | T8.2 | F8 8.10 item 3 |
| T8.4 | report.py -- markdown + JSON output (the demo numbers) + Clopper-Pearson helper (scipy.stats.beta) + tests | benchmark/report.py, benchmark/ci.py | T8.3 | F8 8.10 items 4, 5 |
| T8.5 | ground_truth.schema.json + validation on load + disputes() export + tests | benchmark/ground_truth.schema.json, benchmark/disputes.py | T8.3 | F8 8.10 items 6, 7 |
| T8.6 | benchmark.config (normalization, +-0.3 mm R8 boundary, stratification minimums, subsets 20/10) + BENCHMARK_SKIP_CACHE env flag (default off, fixture asserts) + two-run determinism assertion + tests | config/benchmark.config, benchmark/run.py | T8.2 | F8 8.10 items 8, 9, 10 |
| T8.7 | F8 acceptance fixtures: 10 criteria of F8 8.11 | fixtures/f8/ | T8.3-T8.6 | F8 8.11 |

## Human + parallel tracks

| ID | Task | Track | When | Spec ref |
|---|---|---|---|---|
| H1 | Collect 80-100 labels (stratified: ~10% Hindi, >=10 R5 violations, >=5 exempt sachets, >=10 uncalibrated, >=5 PDFs; ETag dedupe) | H -- benchmark | START day 1; ~30 verified by day 2, rest day 3 | F8 8.6 |
| H2 | 2-labeler ground-truth protocol: independent labeling against the ENGINEERING.md decision tables (compiled 1:1 in backend/docs/CHECKS.md), third-opinion adjudication, measurements with uncertainty | H -- benchmark | with H1 | F8 8.6 |
| H3 | Stability sub-run: 20 labels fresh extraction (BENCHMARK_SKIP_CACHE=1), verdict comparison | H + agent | after T8.2 | F8 8.6 |
| H4 | Live validation: 10-label end-to-end run on the deployed stack; demo numbers cite this | H + agent | after local benchmark passes | F8 8.6 |
| H5 | SIH 2026 PPT deck: problem, solution, live demo flow, impact (PS SIH26034) | H -- demo | day 3 | DECISIONS 0 |
| H6 | Demo video, 3 min, shows where AWS fits (Ship It requirement) | H + FE | by day 4 (20 Sept) | DECISIONS 0 |
| H7 | Writeup: problem, the build, where AWS fits, what we learned + AI tools named | H | by day 4 (20 Sept) | AGENTS 0 |
| F1 | Upload UI: file picker, content-type guard, optional label_width_mm, presigned PUT + progress | FE | after CONTRACTS mocks ready | CONTRACTS 3 |
| F2 | Report card: polling GET /scans/{id} (~2 s), status view, results render (verdicts, citations, evidence, fixes, boxes on display_image), exemption banner, found X of 7 | FE | with backend Phase 5 | CONTRACTS 2 |
| F3 | History/search/stats: GET /scans (query/status/rule_id + pagination), GET /stats views, most-failed rules | FE | after Phase 7 | CONTRACTS 3 |
| F4 | Downloads: report pdf/json/csv via GET /reports links (302 -> S3) | FE | after Phase 6 | CONTRACTS 3 |
| F5 | Deploy React build to labelcheck-web bucket | FE | last | DECISIONS 5 |

## Definition of done (whole project)

All TASKS done + benchmark report (actual N stated) + live validation H4 + demo video (3 min, shows where AWS fits) + writeup (problem, the build, where AWS fits, what we learned + AI tools named).
