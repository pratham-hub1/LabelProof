# PROGRESS.md -- Live State

**Updated:** 2026-09-17 (design phase complete, implementation starting)
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

## Not started

- **Repo code** -- every implementation task, tracked in TASKS.md (all tasks TODO)
- **AWS infra** -- buckets, Lambda (Function URL + S3 trigger), DynamoDB `scans` table + 2 GSIs, IAM users/policies, Lambda layers (Tesseract, reportlab)
- **Benchmark label collection** -- the long-lead human task: 80-100 real supermarket labels, 2-labeler + adjudication protocol, stratified minimums (ENGINEERING F8 8.6). Phasing: ~30 fully-verified labels by day 2, remainder by day 3. START NOW -- it gates the demo numbers.
- **Frontend track** -- builds against CONTRACTS.md only (upload UI, polling report card, history/search/stats, download buttons); may keep its own UI-focused doc

## Open items (DECISIONS.md 9)

1. Final product name (current: LabelCheck, working name)
2. Which member owns Lambda deploys; IAM usernames
3. Exact Bedrock inference profile IDs (wire during integration)

## Decision log

Authoritative log: DECISIONS.md (15 entries, 2026-09-16 to 2026-09-18). Highlights: initial lock; judging criteria; core principle; doc scoping + proof-first rule; Features 1-10 proven and locked; CONTRACTS additive changes (F4, F6, decision sessions); PENDING->FAILED upload-timeout semantics (F5); Rule 7 Table-I legal correction to the 2018 area-based table.

## Next actions (in order)

1. Repo init (today, 17 Sept) -- scaffold per TASKS.md Phase 0; branch protection, `.gitignore`, no code before this date
2. Benchmark collection trip planning -- stratification minimums, 2 labelers, materials (ruler/calipers, phone)
3. Backend: Phase 0 infra + Phase 1 (Feature 1 modules, pure Python, no AWS needed) in parallel -- AWS-unfamiliarity never blocks anyone (DECISIONS.md 7)
4. Frontend: start against CONTRACTS.md mocks in parallel
