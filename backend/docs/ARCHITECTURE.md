# ARCHITECTURE.md -- LabelCheck System Architecture (BACKEND ONLY)

**What this is:** the text architecture document for LabelCheck, written after all 10 features were PROVEN in ENGINEERING.md. It documents the final system as locked in DECISIONS.md + ENGINEERING.md. It invents nothing new: if something is not already locked there, it is not in here.

**Doc scoping:** backend build document. The frontend track builds against CONTRACTS.md only and never reads this file. No schedule or day-planning content.

---

## 1. System Overview

LabelCheck is an assist / self-check tool -- NOT a legally certified replacement for inspectors -- that checks compliance of packaged commodities under the Legal Metrology (Packaged Commodities) Rules, 2011. One line: a label photo or PDF goes in, AI reads it (extraction only), a deterministic rule engine judges it against 11 codified checks (Rules 6-17, Chapter II), and a compliance report card comes out: pass/fail/NA per rule, exact clause citation, violations highlighted on the label image, and fix-it guidance per violation.

The project targets two events with one build: SIH 2026 (PS SIH26034, Ministry of Consumer Affairs, Food & Public Distribution) and the WeMakeDevs x AWS Bharat Builds Tour "First Commit" hackathon, 17-20 Sept 2026 (Ship It track: deployed live on AWS, public repo, 3-minute demo video, writeup).

The user flow in one paragraph: the user photographs a flat packet or carton (or uploads artwork as a PDF), optionally entering the label's physical width in millimetres; the browser uploads the file directly to S3 with a presigned URL; an S3 event triggers the Lambda pipeline, which extracts the declarations with an LLM, verifies every claim deterministically against an OCR word index, applies the exemption layer, runs the 11 checks, and writes the results; the frontend polls until the scan finishes and renders a report card with annotated boxes, per-rule verdicts, citations and fixes, plus downloadable PDF/JSON/CSV reports and a persistent, searchable scan history.

The stack is exactly 4 AWS services, everything in ap-south-1 (Mumbai):

| Service | Role |
|---|---|
| S3 | 3 buckets: labelcheck-uploads (private, label photos/PDFs in), labelcheck-outputs (public-read: annotated images + generated reports), labelcheck-web (static React build). One bucket with mixed permissions is how leaks happen. |
| Lambda | ONE function, invoked two ways: (a) Function URL for the API, routed by path; (b) S3 ObjectCreated trigger for processing. Function URL over API Gateway is a deliberate cost decision. |
| DynamoDB | one `scans` table, PK `scan_id`, plus 2 GSIs (history/brand). |
| Bedrock | extraction only -- fields + boxes + confidence. Haiku first, Sonnet fallback for low-confidence reads, behind one swappable interface. |

No API Gateway, no EventBridge/SNS/queues, no Cognito in the MVP. One extraction call costs well under $0.01; the ~100-label benchmark costs about $1-2.

## 2. Core Principle -- model-independent correctness

This is why the whole architecture exists. The LLM reads the label; code judges it. The judge never hallucinates.

The model's quality may change **coverage** (how many fields get extracted and verified), never **correctness** (whether a given verdict is right). A weak model yields more NA / NEEDS_REVIEW results, never more wrong answers. Every verdict must trace to deterministic verification -- crop-verify OCR on the pixels, or the PDF text layer -- never to raw model output.

Formally (ENGINEERING.md, Feature 1): P(wrong PASS/FAIL verdict per field) <= eps_ocr, a property of the OCR verifier and normalization rules, not of the LLM. The system itself detects incomplete extraction and reports it honestly ("found 5 of 7 declarations"), and the benchmark reports accuracy and coverage as separate numbers. Degradation is a feature: an unreadable field is flagged for rescanning, never guessed.

## 3. Component Deep-Map

The processing pipeline, in order: **ingestion -> preprocess (canonical image) -> OCR word-index -> LLM extraction -> verification gauntlet -> exemption layer + rule engine -> report.**

| Component | Job | Inputs -> Outputs |
|---|---|---|
| Ingestion (Feature 5) | presigned upload + idempotent processing trigger | POST /upload body -> presigned PUT URL (900 s, ContentType-pinned) + PENDING record; S3 event -> size gate -> conditional claim (PENDING -> PROCESSING) |
| Preprocess (Feature 10) | the single canonical image — one coordinate space for every box, the word index, geometry and reports | raw bytes + content_type -> canonical image (photo: EXIF-transposed, original resolution; PDF: page 1 @ 200 DPI, PyMuPDF) |
| Word-index builder (Feature 1) | one full-image deterministic OCR pass | image -> [{word, box, confidence}] (Tesseract via a Lambda layer; pdfplumber on the PDF text layer) |
| LLM extraction (Bedrock) | the ONLY model job: read fields + boxes | image/PDF + prompt -> Extraction JSON (7 declaration fields, raw/parsed/confidence/box); extraction cache keyed by the S3 object ETag -- the same label never hits Bedrock twice |
| Verification gauntlet (Feature 1) | prove or reject every LLM claim | each claim + word index -> VERIFIED / NA(reason) / NEEDS_REVIEW |
| Readability score (Feature 1) | can this image be judged at all? | word index -> R = (words >= 15) AND (mean confidence >= 0.65) |
| Exemption layer (Feature 4) | detect Rule 26(a) / Rule 3 inapplicability | VERIFIED quantity + generic_name -> EXEMPT / NEEDS_REVIEW / NONE |
| Rule engine framework (Feature 3) | field-status pre-resolution + check execution | gauntlet output + readability + exemptions -> field_status map -> 11 check results |
| Checks R1-R7, R11 (Feature 3) | extraction-based verdicts | field_status + patterns.config -> per-rule PASS/FAIL/NA/NEEDS_REVIEW |
| Geometry engine, R8-R10 (Feature 2) | measured verdicts | image + boxes + calibration -> numeral height in mm, exclusion-zone, contrast ratio |
| Report generator (Feature 6) | artifacts | pipeline context -> annotated image, PDF, CSV, JSON, display image -> outputs bucket |
| API + storage (Feature 7) | history, search, stats, artifact serving | records + GSIs -> GET routes, 302 redirects |

**The verification gauntlet, gate by gate (Feature 1):**

| Gate | Check | Catches |
|---|---|---|
| G1 | box sanity -- inside image bounds, non-degenerate | broken geometry |
| G2 | raw text non-empty | empty claims |
| G3 | parsed <-> raw consistency -- digits of `parsed` appear in `raw`; unit token present | parse/claim mismatch |
| G4 | crop-verify -- normalized OCR text inside the claimed box must match the claimed raw (edit distance = 0) | hallucination, misread, wrong box |
| G5 | anchor check -- the box must contain an OCR-detected keyword anchor of the field type | wrong attribution |
| G6 | self-reported confidence >= 0.60 (secondary signal only) | weak reads |

`mrp`, `net_quantity`, `mfg_date`, `consumer_care` are anchored (G5 applies; their labels carry reliable keywords). `manufacturer_name`, `manufacturer_address`, `generic_name` are unanchored (G1-G4 + G6; reported as "unanchored-verified") -- the asymmetry is principled: anchored fields drive numeric/wording verdicts, unanchored fields drive presence verdicts.

**Geometry tiers (Feature 2):** vector PDFs give exact millimetres (pdfplumber char boxes, 1 pt = 0.3528 mm, eps = 0); the required minimum comes from the Rule 7 Table-I class keyed on the principal-display-panel area (as substituted by GSR 629(E), w.e.f. 1.1.2018). Calibrated photos (user-supplied label_width_mm) give measured mm with a 3-sigma confidence band; the 3-sigma rule makes a wrong verdict impossible by construction (H + 3*sigma < required -> FAIL; H - 3*sigma >= required -> PASS; otherwise NEEDS_REVIEW -- the boundary zone never produces a verdict). Uncalibrated photos: R8 = NA with NO_SCALE_REFERENCE; R9 (clear space) and R10 (contrast) are scale-free and always run.

## 4. Data Flow Walkthrough -- one scan's life

1. The browser calls POST /upload with filename, content_type and the optional label_width_mm. The Lambda validates, generates scan_id (SC- + 6 chars, lookalike-free), writes the PENDING record (ConditionExpression attribute_not_exists; collision -> regenerate), and returns a presigned PUT URL (900 s, ContentType pinned into the signature).
2. The browser PUTs the file directly to labelcheck-uploads. Lambda never proxies bytes.
3. The S3 ObjectCreated event invokes the same Lambda on its event path: size gate (event's size field; > 20 MB -> FAILED OVERSIZED_FILE), then the conditional claim -- an atomic test-and-set on status = PENDING -> PROCESSING. Duplicate events, Lambda retries and late deliveries all fail the condition and are skipped. At-least-once S3 delivery + atomic claim = exactly-once pipeline execution.
4. The pipeline runs in that one invocation: preprocess (canonical image) -> word index -> Bedrock extraction (or ETag cache hit) -> gauntlet -> readability -> exemption layer -> the 11 checks -> annotated image + 4 other artifacts -> 5 S3 PUTs to the outputs bucket.
5. ONE terminal write populates results, summary, found_declarations and artifact keys: DONE, NEEDS_REVIEW, or FAILED. Terminal states never change again. A normal exception is caught and written as FAILED with an error object before the invocation ends.
6. The frontend polls GET /scans/{id} (consistent read, ~2 s) until status leaves PENDING/PROCESSING, then renders the report card from the scan record. Stale-state guards on that route convert abandoned states to FAILED (STALE_PROCESSING after 5 min; UPLOAD_TIMEOUT / EVENT_NOT_RECEIVED after 960 s).
7. Report downloads: GET /reports/{scan_id}.{format} -> 302 redirect to the artifact's public S3 URL.

Scan lifecycle: PENDING -> PROCESSING -> DONE | NEEDS_REVIEW | FAILED. A scan that finishes with unresolved ambiguities ends NEEDS_REVIEW -- degradation, never guessing.

## 5. Failure & Degradation Matrix

Every failure mode maps to: what the user sees, the reason code, and what stays guaranteed. The degradation reason codes plus the exemption NA:

| Failure mode | User sees | Reason code | What stays guaranteed |
|---|---|---|---|
| Image too poor to judge | honest "cannot determine" + rescan guidance | UNREADABLE_IMAGE | no false FAIL |
| Field claimed but unconfirmed | this field's NA, rest of report intact | VERIFY_FAILED | partial report principle |
| Weak but clean read | flagged for one human glance | LOW_CONFIDENCE | no guess |
| Devanagari-only field | flagged, not judged | UNSUPPORTED_LANGUAGE | correctness kept |
| Field keyword present but not extracted | flagged for rescan, not judged | EXTRACTION_MISS | no false FAIL |
| Uncalibrated photo | R8 not measured; R9/R10 full results | NO_SCALE_REFERENCE | no wrong mm |
| Required field not VERIFIED | dependent checks NA | DEPENDENCY_UNAVAILABLE | no verdict on missing input |
| Mandatory declaration absent on a readable label | FAIL: "not found on label" (a real violation, never swallowed) | NOT_PRINTED context | the most common real violation is caught |
| Exempt package (<= 10 g/ml, verified non-tobacco) | exempt banner, all checks NA, separate summary count | NA_EXEMPT | an exempt scan never renders as compliant |
| Exemption uncertain (tobacco proviso, > 25 kg/l) | single top-level NEEDS_REVIEW with the reason string | - | no false exemption |
| Scan-level failures | FAILED + error object: OVERSIZED_FILE, STALE_PROCESSING, UPLOAD_TIMEOUT, EVENT_NOT_RECEIVED, EXTRACTION_FAILED, INTERNAL | - | terminal finality; re-upload is the fix path |

Two structural guarantees across every row: a failed gate on one field never fails the scan (only unparseable garbage does -- G0), and every report states "found X of 7 declarations" (summary.found_declarations).

## 6. Design Rationale -- the "why not" section

Rejected alternatives, and what triggered each rejection, so future readers do not re-propose them:

- **Dual-LLM cross-check (A2, Feature 1):** two statistical models have correlated errors; agreement proves nothing; 2x cost; not deterministic.
- **Format validators only (A1, Feature 1):** correctness becomes a function of LLM quality -- a misread like "Rs. 25" passes every format check.
- **OpenCV (Feature 2):** ~100 MB Lambda layer, slow deploys; PIL + numpy + scipy.ndimage cover every primitive needed.
- **API Gateway (DECISIONS 5):** deliberate cost decision for the Ship It pitch; Lambda Function URLs serve the API surface; no throttling needs in the MVP.
- **Amazon Textract (Feature 1, documented upgrade path):** would strengthen verification further, but it is a 5th AWS service -- a team decision per DECISIONS.md is required before ever adopting it. Not in the MVP.

Also rejected along the way, for the record: queues (EventBridge/SNS/SQS -- 4-service lock), OpenSearch for search and counter-based stats (scale redesign is roadmap; the locked design documents its ceiling), event-ID dedup for idempotency (keys the wrong dimension -- the state-based conditional claim won), a coin in frame for scale (adds a second CV problem to the most delicate feature), full guided capture (three instructions users will not follow; two of three are measured internally), and photo-R8-always-NA (kept only as the pre-agreed shrink if calibration proves flaky).

## 7. Boundaries & References

What LabelCheck deliberately does NOT do:

- **Uncalibrated absolute sizes** -- absolute millimetres cannot be recovered from an uncalibrated photo (a physical impossibility, not an algorithmic gap); the law defines no ratio alternative for R8.
- **Non-planar packages** -- the photo path's geometry assumes the front face lies in one plane; curved surfaces (bottles, jars) are roadmap. The PDF/artwork path supports any shape.
- **Undetectable exemptions** -- institutional/industrial packages, DPCO formulations, hotel food, agricultural produce above 50 kg, thread coils, loose garments cannot be detected from a label; the report footer states "This tool assumes non-exempt retail packaged goods."
- **Not legal advice** -- an assist / self-check tool; where the law is ambiguous, the system says NEEDS_REVIEW, never a wrong FAIL (the interpretation registry documents all four calls).
- **Out of MVP scope** -- wholesale/export packages, the full exemption matrix, e-commerce listing checks, FSSAI labelling, mobile app, batch upload, Cognito auth (stretch only).

References: DECISIONS.md (constitution -- every session starts by re-reading it), CONTRACTS.md (frozen data contracts; the only shared doc), ENGINEERING.md (proven designs, Features 1-10), backend/docs/CHECKS.md (exact per-check spec), and the LMPC (PC) Rules 2011 gazette text (WB gazette PDF of the 2011 Rules; amendments noted where relevant).
