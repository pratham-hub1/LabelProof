# Nex Final Pass — Day 3 Findings

## Step 1 — Wrong-verdict construction
done | findings: 6 | requests: ~7/40 | plan: 25%

### Findings
1. **Rotated portrait labels can produce a wrong R8 PASS.** `backend/src/geometry/calibrate.py` assigns the horizontal PCA extent to physical width. For a 50 x 100 mm label rotated 90 degrees, the probe returned `scale=49.98 px/mm` and `pdp_area_cm2=12.495` instead of 50 cm2. A 2.0 mm numeral was judged against the 1.0 mm class and returned PASS; the correct 50 cm2 class requires 1.5 mm. This is a silent false PASS path.
2. **The rotation sanity check is not wired into the pipeline.** `calibrate_photo(..., word_index=None)` skips the 0.5-4.0 mm body-text sanity gate, so gross orientation/scale errors can reach a verdict instead of degrading to NA.
3. **R8 area-straddle handling is safe but not contract-exact at exact PDF boundaries.** `get_required_mm_candidates` always applies 7% area uncertainty, including exact vector-PDF boundaries. At A=50, 100, and 2500 it returns both adjacent classes and `NEEDS_REVIEW`; the locked PDF rule requires the less-strict class. This is coverage/spec drift rather than a demonstrated false FAIL.
4. **Exemption is bypassed in the deployed pipeline path.** `backend/src/pipeline/main.py` passes raw gauntlet statuses directly to `run_checks` and never calls `resolve_field_statuses`. A verified 10 g non-tobacco sachet returned exemption `EXEMPT` but all seven rule checks PASS and terminal status DONE. The contract requires all results NA_EXEMPT and an exempt banner/count.
5. **Uncertain exemptions are also ignored by final status.** The same raw-status path does not propagate `NEEDS_REVIEW` from a tobacco sachet or >25 kg/l quantity; a clean rule result can still become DONE.
6. **Final status ignores NEEDS_REVIEW results.** `main.py` chooses DONE whenever `summary.fail == 0`; an ambiguous R1 address or any other NEEDS_REVIEW result with no FAIL is therefore reported DONE, violating the locked scan-level rule.

## Step 2 — B1-B8 and pipeline wire-up
done | findings: 3 | requests: ~12/40 | plan: 45%

### Item verdicts
- **B1 R1 dependencies — FIXED.** `requires=["manufacturer_name", "manufacturer_address"]`; unreadable-address probe returns NA/DEPENDENCY_UNAVAILABLE.
- **B2 R2 dependencies — FIXED.** `requires=["generic_name"]`; unreadable-name probe returns NA/DEPENDENCY_UNAVAILABLE.
- **B3 R6 dependencies — FIXED.** `requires=["consumer_care"]`; unreadable-contact probe returns NA/DEPENDENCY_UNAVAILABLE.
- **B4 R11 scope — FIXED.** Only `net_quantity.raw` is checked; the existing "About Nuts" fixture passes.
- **B5 R3 sub-kg — FIXED.** `0.5 kg` returns FAIL with the locked fix.
- **B6 R5 — PARTIALLY FIXED.** Shorthand/taxes behavior is fixed, and two values in one raw string return NEEDS_REVIEW. The required whole-word-index anchor sweep for distinct MRP values is still missing: two separate anchored `MRP Rs. 20` / `MRP Rs. 30` regions with a one-value claim return FAIL instead of NEEDS_REVIEW.
- **B7 rotated numeral measurement — PARTIALLY FIXED.** PCA rotation support was added, but tight axis-aligned crops still return `0.0` because the mask is flipped when ink occupies most of the crop. A 45-degree control returns 100.4 px.
- **B8 exemption tests — FIXED.** Signature and dictionary-return assertions are updated; focused suite passes.
- **Pipeline wire-up — NOT FIXED.** `backend/src/pipeline/main.py` still embeds a mock Bedrock caller, never resolves field statuses/exemptions, never runs R8-R10, and derives DONE from `fail == 0`. Its end-to-end test asserts only that five artifacts exist and status is DONE/NEEDS_REVIEW.

### Verification
- `PYTHONPATH=backend .venv/Scripts/python.exe -m pytest -q backend/tests/rules backend/tests/geometry backend/tests/gauntlet backend/tests/acceptance/test_f1.py backend/tests/acceptance/test_f2.py backend/tests/acceptance/test_f3.py backend/tests/acceptance/test_f4.py` -> **116 passed**.
- Focused adversarial probes covered dependency short-circuiting, R3/R5 tiers, exemption thresholds, rotated calibration, R8 class intervals, and tight rotated measurement.

### API/contract audit
- `GET /scans` and search return `next_key`; `CONTRACTS.md` and the frontend contract require `last_key`.
- The frozen scan contract defines `results` as an array of 11 objects, while the engine/artifact/API path uses a rule-ID dictionary and currently emits only R1-R7/R11.
- Exemption output is `{status, reason}` internally, while the contract requires `{applied, citation, reason}`; report code separately expects `{applied, rule}`.
- Five of six scan error codes have an emission path. `EXTRACTION_FAILED` is raised by the extraction client but the handler converts the resulting pipeline exception to `INTERNAL`; G0 also emits non-contract `G0_SCHEMA_INVALID`.
- `frontend/` contains only `.gitkeep`; endpoint consumption, field rendering, and FE build readiness are not covered.

## Step 3 — Mocked user journey
done | findings: 5 | requests: ~19/40 | plan: 70%

### Journey verdicts
- **Wrong file type — FIXED.** `POST /upload` returns 400 `BAD_REQUEST` before creating a record.
- **Huge file — FIXED.** An S3 event with `size=20,971,521` marks the scan FAILED with `OVERSIZED_FILE`; polling returns the terminal error body.
- **Double submit — FIXED.** The first event returns `success`; the duplicate returns `skipped` through the conditional claim.
- **Polling a failed scan — FIXED.** The failed record is returned with `status=FAILED` and the error object.
- **Normal upload -> artifacts -> stats — NOT FIXED.** The first event reaches the pipeline, then fails on DynamoDB `Decimal` serialization while building the JSON artifact. Polling the resulting PROCESSING record also raises `TypeError` in `serialize`. With a stubbed PDF import, the same Decimal failure occurs; the normal journey never reaches five artifacts or stats.

### Verification
- Mocked journey covered POST validation, presign response, S3 event processing, duplicate delivery, polling, oversized failure, and error visibility.
- `PYTHONPATH=backend .venv/Scripts/python.exe -m pytest -q backend/tests/ingestion backend/tests/acceptance/test_f5.py backend/tests/acceptance/test_f6.py backend/tests/acceptance/test_f7.py backend/tests/acceptance/test_pipeline.py` -> **32 passed, 1 failed**; the failure is missing `fitz` in `test_pipeline_end_to_end`.

## Step 4 — Provider swappability
done | findings: 4 | requests: ~23/40 | plan: 82%

### Verdict
**PARTIALLY FIXED.**

- The `extract(..., model_client=...)` seam and Haiku/Sonnet fallback are testable without Bedrock; `backend/tests/acceptance/test_f9.py`, `test_bedrock.py`, and `test_run.py` pass (**16 passed**).
- `backend/src/extraction/client.py` still hardcodes Bedrock model-ID defaults and leaves `call_bedrock` as a placeholder; model IDs are not loaded from config as required.
- `backend/src/gauntlet/bedrock.py` is a second, stale provider-specific implementation with old model IDs and no Converse/toolConfig path. It is currently unused, but violates the one-client boundary and is one import away from re-entering production.
- `backend/src/pipeline/main.py` defines an internal mock Bedrock caller and has no mock/live provider switch. Swapping providers requires editing orchestration code.
- `run_gauntlet` performs only shallow schema checks and applies them after cache lookup; malformed cached/external-provider output can bypass the client’s full `jsonschema` validation. Rules, geometry, and API have no direct provider imports, so the leak is confined to extraction/orchestration today.

No live Bedrock or AWS invocation was made.

## Step 5 — Final B#/S#/N# report
done | findings: 19 | requests: ~30/40 | plan: 100%

### B# — silent wrong-verdict or release blockers

**B1 — Rotated labels can produce a false R8 PASS.**
- File: `backend/src/geometry/calibrate.py:15-45,136-157`
- Why: PCA’s horizontal extent is always treated as physical label width. A 50 x 100 mm label rotated 90 degrees calibrated to 12.495 cm2; a 2.0 mm numeral passed against the 1.0 mm class instead of the correct 1.5 mm class.
- Fix: retain both PCA axes, map the user-supplied physical width to the correct axis (or require explicit orientation), and return NA when the mapping is ambiguous. Add portrait and 90-degree fixtures.

**B2 — Tight digit crops can measure zero height.**
- File: `backend/src/geometry/measure.py:33-37`
- Why: the binary mask is flipped solely because ink is the majority of a tight crop. Tight 0-degree and 90-degree components returned `0.0`; the 45-degree control returned 100.4 px.
- Fix: determine foreground from component/border evidence rather than crop-area majority; preserve rotation-invariant PCA height and test tight/padded crops separately.

**B3 — Exemptions are bypassed in the pipeline.**
- File: `backend/src/pipeline/main.py:61-77,96`
- Why: raw gauntlet statuses are passed to `run_checks`; `resolve_field_statuses` is never called. A verified 10 g non-tobacco sachet produced seven PASS results and terminal DONE despite `EXEMPT`.
- Fix: resolve statuses before checks, convert exemption output to the contract shape, short-circuit all R1-R11 results to NA_EXEMPT, and propagate uncertain exemptions to NEEDS_REVIEW.

**B4 — The final verdict ignores NEEDS_REVIEW.**
- File: `backend/src/pipeline/main.py:96`; correct helper exists at `backend/src/rules/verdict.py:1-25` but is unused.
- Why: DONE is selected whenever there is no FAIL. Any ambiguous result with no FAIL becomes DONE.
- Fix: use the locked terminal-state helper: any NEEDS_REVIEW result or uncertain exemption -> NEEDS_REVIEW; otherwise DONE only when no FAIL exists.

**B5 — The deployed rule set is incomplete.**
- File: `backend/src/pipeline/main.py:70-82`; registry implementation at `backend/src/rules/engine.py:31-46`.
- Why: the pipeline does not explicitly register checks and does not run R7, R8, R9, or R10. The contract requires exactly 11 results; the current path can emit seven, fewer, or an empty registry depending on incidental imports.
- Fix: make registry composition explicit, run all 11 checks including geometry and R7, and validate the result count/IDs before artifact generation.

**B6 — R6 can PASS without a phone or email.**
- File: `backend/src/rules/checks/r6_r11.py:7-15`
- Why: any VERIFIED consumer-care raw value returns PASS; `Consumer Care:` and `Consumer Care: no contact` both passed in probes.
- Fix: require parsed phone OR email for PASS, FAIL with the configured contact fix when neither exists, and preserve NA for unreadable dependencies.

**B7 — R5 does not implement the locked multi-MRP sweep.**
- File: `backend/src/rules/checks/r5.py:14-35`
- Why: it counts price-like tokens only in the claimed raw string. Two separate anchored word-index regions with distinct values returned FAIL instead of NEEDS_REVIEW.
- Fix: sweep all MRP-anchor regions in the word index, parse each value, and return NEEDS_REVIEW for at least two distinct values.

**B8 — Future manufacturing dates PASS.**
- File: `backend/src/rules/checks/r4.py:20-31`
- Why: the check only parses the format; `MFG 01/2099` returned PASS although the decision table requires NEEDS_REVIEW for future dates.
- Fix: validate year/date plausibility after parsing and route implausible dates to NEEDS_REVIEW using record time, not an uncontrolled wall-clock read.

**B9 — A valid city-only address can FAIL R1.**
- File: `backend/src/rules/checks/r1.py:21-32`
- Why: the implementation checks PIN and state list only, not the documented city/state pattern or region analysis. `123 Main St, Nagpur` returned FAIL.
- Fix: add configurable city/region defenses and the documented dilated-box region check; keep ambiguity as NEEDS_REVIEW.

**B10 — Normal artifact generation and polling fail on Decimal values.**
- Files: `backend/src/pipeline/artifacts.py:68-72`, `backend/src/api/serialize.py:16-24`, `backend/src/api/get_scan.py:43`
- Why: DynamoDB `Decimal` values reach `json.dumps` in both the JSON report and polling response. The mocked journey failed before artifacts/stats and polling raised TypeError.
- Fix: normalize DynamoDB scalars at the deserialization/serializer boundary and add an end-to-end POST/event/poll test with numeric input fields.

**B11 — PDF preprocessing is not available in the active environment.**
- File: `backend/src/preprocess/canonical.py:3`
- Why: unconditional `import fitz` blocks the full suite and pipeline even for image uploads; Feature 10 is marked complete but the dependency is absent from the active venv/layer.
- Fix: install/pin PyMuPDF in the runtime layer and venv, or lazy-import it only for PDF content; verify both image and PDF preprocess paths.

**B12 — Benchmark harness cannot start.**
- File: `backend/benchmark/run.py:26`
- Why: it imports removed `src.reports.pdf.generate_pdf`; the command fails immediately, so demo accuracy/coverage numbers cannot be produced.
- Fix: rewire the harness to the current report builder and current `run_checks`/verdict interfaces, then run the deterministic replay and report commands.

### S# — contract/spec regressions

**S1 — Results are dictionaries, not the frozen array contract.**
- Files: `CONTRACTS.md:163-166`, `backend/src/rules/engine.py:26-51`, `backend/src/reports/pdf.py:91-110`
- Why: code and tests use rule-ID dictionaries; the contract requires an array of 11 objects with `rule_id`, `name`, `citation`, `status`, `evidence`, `fix`, `box`, and `measurement`.
- Fix: introduce one contract adapter at the pipeline boundary and validate all 11 items before persistence.

**S2 — Exemption shapes disagree across modules.**
- Files: `backend/src/rules/exemptions.py:3-7`, `backend/src/pipeline/artifacts.py:41`, `backend/src/reports/pdf.py:78-80`, `CONTRACTS.md:162`
- Why: exemption logic emits `{status, reason}`, artifacts/reports expect `{applied, rule}`, and the contract requires `{applied, citation, reason}`.
- Fix: normalize once after `evaluate_exemptions` and use that shape everywhere.

**S3 — Pagination response key is wrong.**
- Files: `backend/src/api/list_scans.py:54-62`, `backend/src/api/search.py:70-125`, `CONTRACTS.md:206-212`
- Why: API returns `next_key`; the frozen contract and frontend expectation use `last_key`.
- Fix: return `last_key` (or a documented compatibility alias during migration) and update tests/frontend mocks together.

**S4 — Scan error-code mapping is incomplete.**
- Files: `backend/src/extraction/client.py:101`, `backend/src/gauntlet/run.py:40`, `backend/lambda/handler.py:157`, `CONTRACTS.md:167`
- Why: `EXTRACTION_FAILED` is raised below the pipeline but becomes INTERNAL in the handler; G0 emits non-contract `G0_SCHEMA_INVALID`. Only five of six contract codes have a direct path.
- Fix: map extraction/G0 failures to the approved contract code and test all six codes at the handler boundary.

**S5 — Provider swappability is only partial.**
- Files: `backend/src/extraction/client.py:54-101`, `backend/src/gauntlet/bedrock.py:1-85`, `backend/src/pipeline/main.py:30-51`
- Why: model IDs are hardcoded defaults, `call_bedrock` is a placeholder, a stale Bedrock-specific module remains, and the pipeline embeds a mock caller with no mock/live switch.
- Fix: one provider interface, config-driven model IDs, explicit mock/live selector, and remove or quarantine the duplicate Bedrock module.

**S6 — Gauntlet G0 is weaker than the extraction client schema.**
- File: `backend/src/gauntlet/run.py:7-40`
- Why: cache hits and caller output receive only shallow checks; malformed external-provider output can bypass `EXTRACTION_SCHEMA` and reach field mapping.
- Fix: run full schema validation before accepting cache or provider output and return the approved extraction failure code.

**S7 — Exact PDF R8 boundaries are not implemented.**
- File: `backend/src/geometry/check_r8.py:4-35`
- Why: 7% area uncertainty is always applied, so exact A=50/100/2500 PDFs straddle classes and return NEEDS_REVIEW instead of the locked less-strict class.
- Fix: pass source/uncertainty explicitly; use exact class lookup for PDFs and 3-sigma candidate classes only for photos.

**S8 — A tenth reason code leaks from the engine.**
- File: `backend/src/rules/engine.py:49-51`
- Why: unexpected check exceptions emit `CHECK_ERROR`, outside the locked nine-code set.
- Fix: contain check errors as NEEDS_REVIEW using an approved existing reason (or make an owner-approved contract change) and preserve diagnostics separately.

### N# — coverage and readiness notes

**N1 — Frontend contract consumption is not verifiable.** `frontend/` contains only `.gitkeep`; no upload, polling, report, history, stats, or download implementation can be checked before the stated FE build.

**N2 — Full-suite and determinism verification remain partial.** Full `pytest` is blocked by missing `fitz`; focused runs passed 116 rule/geometry/gauntlet tests, 32 API/ingestion/report tests with one fitz failure, 16 provider tests, and 5 determinism tests when preprocess collection was excluded. The complete repository determinism command was not green.

**N3 — No live Bedrock/AWS calls were made.** Provider, deployment, presigned PUT, S3 trigger, DynamoDB conditional writes, and real Lambda behavior remain unverified by design for this pass; mocked behavior is documented above.

### Coverage
Covered: B1-B8 diff/test verification, rotated and tight-crop geometry probes, R8 sigma/class-boundary probes, exemption edges (10 g, >25 kg/l, tobacco), rule-status/final-verdict construction, mocked upload/presign/event/poll/stats journey, failure modes (wrong type, huge file, duplicate submit, failed poll), API contract comparison, provider mock tests, and determinism subset.

### Not covered
Live Bedrock inference, real AWS IAM/S3/DynamoDB/Lambda deployment, browser/frontend build and rendering, real OCR quality/coverage, benchmark label collection and adjudication, PDF vector geometry, and the full repository test suite with PyMuPDF installed.

requests used: ~30/40
percent: 75%
