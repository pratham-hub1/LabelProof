# PROGRESS.md -- Live State

**Updated:** 2026-09-20 (implementation complete, deployed live on AWS)
**Rule:** this file is the live state of the build -- updated after EVERY task (AGENTS.md 5). The authoritative decision log lives in DECISIONS.md; it is never duplicated here.

---

## Current phase

**DESIGN COMPLETE -> IMPLEMENTATION STARTING.** All 10 backend features are PROVEN and locked. Repo code is allowed from 17 Sept 2026 (the event window is open -- DECISIONS.md 0).

## Done (design)

| Item | State |
|---|---|
| DECISIONS.md | constitution locked; 12 decision-log entries (latest: Features 5-8, 2026-09-17) |
| CONTRACTS.md | frozen v1.0 + 3 approved additive changes (F4 `exemption` object; F6 `display_image` + `found_declarations`) |
| ENGINEERING.md | all 10 features PROVEN: 1 extraction verification gauntlet (2026-09-16), 2 geometry engine, 3 rule engine + checks, 4 exemption layer, 5 ingestion path, 6 report generator, 7 API + storage, 8 benchmark harness (all 2026-09-17), 9 extraction module, 10 preprocess (2026-09-18) |
| backend/docs/CHECKS.md | 11-check exact spec, compiled from ENGINEERING decision tables, drift-verified |
| backend/docs/ARCHITECTURE.md | 7 approved sections, ASCII-only, verified against core docs |
| AGENTS.md | agent constitution + verify commands, created 2026-09-17 |
| PROGRESS.md / TASKS.md | created 2026-09-17 |
| Docs consistency pass | 2026-09-17 — mechanical syncs from external review applied (details: DECISIONS.md decision log); open design items remain (extraction feature, preprocess, cache store, field-status bridge, σ base, 200 g boundary, scan-level NEEDS_REVIEW rule, measurement schema, brand_guess, ground-truth shape, minAreaRect, embossed detector, R1 name role, R7 threshold, R5 mechanism, anchors content) |
| Design decision session | 2026-09-17 — 11 decisions + 2 approach calls locked (decision log); docs synced: field-status bridge, R1/R5/R7/R8 specs, σ = 0.05 × H, 200 g boundary, scan-level NEEDS_REVIEW rule, CONTRACTS additive changes (brand_guess, summary.exempt, measurement schema, EXTRACTION_FAILED / EXTRACTION_MISS). Remaining design: Feature 9 extraction, preprocess, minAreaRect, embossed detector, ground-truth shape |
| Design + legal-correction pass | 2026-09-18 — 12 decisions (D12–D23) applied (decision log): R8 migrated to the 2018 area-based Rule 7 Table-I (GSR 629(E); supersedes the 200 g boundary decision), Features 9 (extraction module) + 10 (preprocess) written and PROVEN, class-interval rule, embossed/molded detector, minAreaRect spec, CONTRACTS §5 fixture shape, anchors + taxes initial content, unanchored-verified tag, PDF ink-coverage for R9, TASKS rewiring (T1.8/T1.9, H5–H7), model-ID defaults. Docs now implementation-complete |
| T0.1 | Repo init — monorepo layout (frontend/ + backend/), 8 docs placed (L_6), folder skeleton per TASKS, .gitignore + README stub; §8 layout locked in the decision log | 2026-09-18 | DECISIONS 0, 8; decision log |
| T0.3 | 3 S3 buckets infra configs + scripts | 2026-09-18 | F5, F6, F7 |
| T0.4 | DynamoDB scans table infra script | 2026-09-18 | F7 |
| T0.5 | Lambda skeleton & infra configs | 2026-09-18 | F5 |
| T0.6 | Lambda layers requirements | 2026-09-18 | F1, F6, F8, F10 |
| T0.7 | Bedrock access check script (blocked invoke) | 2026-09-18 | F9 |
| T1.1 | Word-index builder (Tesseract + pdfplumber) and tests | 2026-09-18 | F1 1.9 item 1 |
| T1.2 | Gates G1-G6 pure functions and tests | 2026-09-18 | F1 1.9 item 2 |
| T1.3 | anchors.config + loader + tests | 2026-09-18 | F1 1.9 item 3 |
| T1.4 | reasons.config + result mapper + tests | 2026-09-18 | F1 1.9 items 4, 6 |
| T1.5 | Readability score + tests | 2026-09-18 | F1 1.9 item 5 |
| T1.6 | Extraction cache interface + tests | 2026-09-18 | F1 1.9 item 7 |
| T1.7 | F1 acceptance fixtures (hallucination, misread, missing, etc) + tests | 2026-09-18 | F1 1.10 |
| T1.8 | Main gauntlet orchestrator + tests | 2026-09-18 | F1 1.9 item 8 |
| T1.9 | preprocess(raw_bytes, content_type) -> canonical image + tests | 2026-09-18 | F10 |
| T2.1 | measure_numeral_height + tests | 2026-09-18 | F2 2.7 item 1 |
| T2.6 | thresholds.config + loader + tests | 2026-09-18 | F2 2.7 item 6 |
| T2.7 | F2 acceptance fixtures + tests | 2026-09-18 | F2 2.8 |
| T2.2 | calibrate_photo + tests | 2026-09-18 | F2 2.7 item 2 |
| T2.3 | check_r8 + tests | 2026-09-18 | F2 2.7 item 3 |
| T2.4 | check_r9 + tests | 2026-09-18 | F2 2.7 item 4 |
| T2.5 | check_r10 + tests | 2026-09-18 | F2 2.7 item 5 |
| T3.1 | resolve_field_statuses + tests | 2026-09-18 | F3 3.7 item 1 |
| T3.2 | run_checks framework + tests | 2026-09-18 | F3 3.7 items 2, 3, 5 |
| T3.7 | patterns.config + loader + tests | 2026-09-18 | F3 3.7 item 4 |
| T3.3 | Checks R1 + R2 + tests | 2026-09-18 | F3 3.3 |
| T3.4 | Checks R4 + R5 + tests | 2026-09-18 | F3 3.3 |
| T3.5 | Checks R6 + R11 + tests | 2026-09-18 | F3 3.3, 3.6 |
| T3.6 | Checks R3 + tests | 2026-09-18 | F3 3.3 |
| T3.8 | F3 acceptance fixtures | 2026-09-18 | F3 3.8 |
| T4.1 | evaluate_exemptions + tests | 2026-09-18 | F4 4.8 |
| T4.2 | tobacco.config | 2026-09-18 | F4 4.8 |
| T4.3 | F4 acceptance fixtures | 2026-09-18 | F4 4.9 |
| T1.8 | Bedrock extraction client (schema, prompt, fallback logic) | 2026-09-18 | F9 |

## Remaining

- **Benchmark label collection** -- corpus collection and calibration pending; framework is production-ready (F8). No accuracy numbers claimed until corpus is collected.
- **Bedrock re-enable** -- on hold per Decision #17; can be added as a config row + dialect adapter when in-region access is confirmed.

## Open items (DECISIONS.md 9)

1. ~~Final product name~~ -- closed: **LabelProof**
2. ~~Exact Bedrock inference profile IDs~~ -- superseded by Decision #17 (Gemini primary, NIM fallback; Bedrock on hold)
## Decision log

Authoritative log: DECISIONS.md (15 entries, 2026-09-16 to 2026-09-18). Highlights: initial lock; judging criteria; core principle; doc scoping + proof-first rule; Features 1-10 proven and locked; CONTRACTS additive changes (F4, F6, decision sessions); PENDING->FAILED upload-timeout semantics (F5); Rule 7 Table-I legal correction to the 2018 area-based table.

## Next actions

1. Benchmark label collection -- collect corpus for calibration against the production pipeline (framework ready, F8)
2. Bedrock re-enable -- config row + dialect adapter once in-region access is confirmed (post-hackathon)
3. Roadmap -- auto-orientation, mobile capture UX, batch scans


| T5.1 | generate_scan_id and PENDING record | 2026-09-18 | F5 |
| T5.2 | presign_upload | 2026-09-18 | F5 |
| T5.3 | claim_scan | 2026-09-18 | F5 |
| T5.4 | mark_terminal | 2026-09-18 | F5 |
| T5.5 | reap_stale_processing, reap_stale_pending | 2026-09-18 | F5 |
| T5.6 | ingestion.config + tests | 2026-09-18 | F5 |
| T5.7 | handler.py (upload & s3 event) | 2026-09-18 | F5 |
| T5.8 | F5 acceptance fixtures | 2026-09-18 | F5 |
| T6.1 | render_annotated (boxes, grouping, colors, banner) | 2026-09-18 | F6 |
| T6.2 | render_display_image (max edge 1600) | 2026-09-18 | F6 |
| T6.3 | sanitize_pdf_text + build_pdf_report (invariant mode) | 2026-09-18 | F6 |
| T6.4 | build_csv_report (RFC 4180 + BOM) + JSON serializer | 2026-09-18 | F6 |
| T6.5 | reports.config + summary logic | 2026-09-18 | F6 |
| T6.6 | Pipeline wiring (5 in-memory artifacts -> S3 PUTs) | 2026-09-18 | F6 |
| T6.7 | F6 acceptance fixtures | 2026-09-18 | F6 |
| T7.1 | router.py (method, path) dispatch, trailing-slash strip | 2026-09-18 | F7 |
| T7.2 | list_scans (GSI-1 query, filters, cursor encode/decode) | 2026-09-18 | F7 |
| T7.3 | search_scans (GSI-2 prefix + Scan fallback, limit looping) | 2026-09-18 | F7 |
| T7.4 | get_scan (consistent GetItem + reaper wiring) | 2026-09-18 | F7 |
| T7.5 | get_stats (Scan + aggregate + warm cache) | 2026-09-18 | F7 |
| T7.6 | redirect_report (status check -> 302 Location) | 2026-09-18 | F7 |
| T7.7 | serialize + normalize_key | 2026-09-18 | F7 |
| T7.8 | api.config + F7 acceptance fixtures | 2026-09-18 | F7 |
| T8.1 | collect_driver.py (upload, poll, harvest API integration) | 2026-09-18 | F8 |
| T8.2 | run.py offline replay logic | 2026-09-18 | F8 |
| T8.3 | score.py metrics and R8 boundary logic | 2026-09-18 | F8 |
| T8.4 | report.py JSON/Markdown output + Clopper-Pearson | 2026-09-18 | F8 |
| T8.5 | ground_truth.schema.json + disputes export | 2026-09-18 | F8 |
| T8.6 | benchmark.config + SKIP_CACHE env check | 2026-09-18 | F8 |
| T8.7 | test_f8.py Acceptance criteria | 2026-09-18 | F8 |
| BEDROCK BLOCKED | Live AWS invoke on hold due to ValidationException on AWS side (owner: teammate) | - | F9 |
| T6.6 Wiring | `main.py` wires the entire real pipeline end-to-end | 2026-09-19 | TASKS.md |
| Phase 1-4 Fixes | B1-B13 | 2026-09-18 | REVIEW_PHASES_1_4.md |
| Phase 5-8 Fixes | B1-B8 | 2026-09-19 | REVIEW_PHASES_5_8.md |
| Day 3 Fixes | N-B1..N-B12, N-S1..N-S8 | 2026-09-19 | nex_findings_day3.md |
| T1.8 | Replaced Bedrock client with OpenAI-compatible client (GEMINI/NIM), robust JSON extraction, + mocked tests | 2026-09-19 | F9 |
| Lambda Deployment | Live E2E fixes (fixed handler.py error_code, switched USE_MOCK_BEDROCK to live, fixed label width, restored numpy.testing for scipy) | 2026-09-20 | E2E |
