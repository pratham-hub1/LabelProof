# CONTRACTS.md — Data Contracts (FROZEN v1.0)

These are the frozen data contracts for LabelCheck. Backend and frontend build in parallel against them. **Changing anything in this file = team decision + an entry in the DECISIONS.md decision log + a note in PROGRESS.md.** No agent may change this file.

Conventions:
- All keys are `snake_case`, always lowercase.
- **Every field key always exists in the JSON.** A field that was not found on the label has value `null` — a missing key is a bug, not "not found".
- Timestamps are ISO 8601 UTC strings (`2026-09-18T14:22:05Z`).
- Coordinates are pixel offsets `[x1, y1, x2, y2]` from the **top-left corner** of the processed image, in this order: left, top, right, bottom. Boxes are `null` when the field has no location.
- Image dimensions MUST travel with boxes — the frontend normalizes with them.
- `confidence` is a float `0.0`–`1.0`.

---

## 1. Extraction JSON

**Who produces it:** the extraction stage (Bedrock call + validators). **Who consumes it:** the rule engine, the annotation stage, the cache. This shape is what gets cached and what `fixtures/` contains.

```json
{
  "schema_version": "1.0",
  "source_type": "photo",
  "image": { "width": 4000, "height": 3000 },
  "language": "en",
  "fields": {
    "manufacturer_name": {
      "raw": "Haldiram's Foods International Pvt. Ltd.",
      "parsed": null,
      "confidence": 0.95,
      "box": [812, 2210, 2890, 2270]
    },
    "manufacturer_address": {
      "raw": "Plot No. 12, MIDC, Nagpur, Maharashtra - 440010",
      "parsed": null,
      "confidence": 0.88,
      "box": [790, 2280, 2950, 2400]
    },
    "generic_name": {
      "raw": "Aloo Bhujia (Savoury Snack)",
      "parsed": null,
      "confidence": 0.91,
      "box": [920, 640, 2600, 700]
    },
    "net_quantity": {
      "raw": "Net Wt. 200 g",
      "parsed": { "value": 200, "unit": "g" },
      "confidence": 0.97,
      "box": [1580, 810, 2210, 880]
    },
    "mrp": {
      "raw": "MRP Rs. 20",
      "parsed": { "value": 20.00, "currency": "INR" },
      "confidence": 0.94,
      "box": [1560, 940, 2240, 1010]
    },
    "mfg_date": {
      "raw": "MFG 08/2026",
      "parsed": { "month": 8, "year": 2026 },
      "confidence": 0.86,
      "box": [1620, 1060, 2180, 1120]
    },
    "consumer_care": {
      "raw": "Consumer Care: 1800-XXX-XXXX, care@haldirams.com",
      "parsed": { "phone": "1800-XXX-XXXX", "email": "care@haldirams.com" },
      "confidence": 0.83,
      "box": [840, 2700, 2900, 2760]
    }
  }
}
```

### Field rules

| Field | `raw` | `parsed` |
|---|---|---|
| `manufacturer_name` | exactly as printed | always `null` (R1 checks the raw text) |
| `manufacturer_address` | exactly as printed | always `null` (R1 checks completeness on raw) |
| `generic_name` | exactly as printed | always `null` (R2 presence check) |
| `net_quantity` | exactly as printed | `{value: number, unit: string}` — unit one of `g`, `kg`, `ml`, `l`, `pcs` |
| `mrp` | exactly as printed | `{value: number, currency: "INR"}` (R5 checks wording on raw) |
| `mfg_date` | exactly as printed | `{month: 1-12, year: number}` (R4 checks format on raw) |
| `consumer_care` | exactly as printed | `{phone: string|null, email: string|null}` |
| `brand_guess` | exactly as printed, or `null` | always `null` — optional search hint, NOT a declaration: never gauntlet-verified, never counted in `found_declarations`; powers `product.brand_guess` (additive — decision log 2026-09-17) |

### Validation gates (run BEFORE the rule engine)

1. Whole document must parse as JSON and validate against this schema — else scan is `FAILED`.
2. `net_quantity.parsed.unit` must be in the allowed unit list — else rule R3 reports the unit problem.
3. `mrp.parsed.value` must be a positive number.
4. `mfg_date.parsed.month` in 1–12, year in 2000–2100.
5. A field with `confidence < 0.60` and non-null raw → that field's status is `NEEDS_REVIEW`; its dependent checks return `NA` with reason `DEPENDENCY_UNAVAILABLE` (do not guess).
6. PDFs: each page becomes its own extraction JSON with `source_type: "pdf"`; `image` refers to that page's rendered image.

---

## 2. Scan Record

One row in DynamoDB (`scans` table, PK `scan_id`) **and** the response body of `GET /scans/{id}` — identical shape.

```json
{
  "scan_id": "SC-8F3K2",
  "status": "DONE",
  "created_at": "2026-09-18T14:21:40Z",
  "updated_at": "2026-09-18T14:22:05Z",
  "input": {
    "filename": "bhujia_front.jpg",
    "content_type": "image/jpeg",
    "source_type": "photo",
    "label_width_mm": 90,
    "s3_key": "uploads/SC-8F3K2.jpg",
    "size_bytes": 1834567
  },
  "product": {
    "brand_guess": "Haldiram's",
    "generic_name": "Aloo Bhujia"
  },
  "extraction": { "...": "the full Extraction JSON from section 1, inline" },
  "summary": { "pass": 7, "fail": 3, "na": 1, "needs_review": 0, "found_declarations": 7, "exempt": 0 },
  "results": [
    {
      "rule_id": "R5",
      "name": "MRP prescribed wording",
      "citation": "Rule 2(m), 6(1)(e) — LMPC (PC) Rules, 2011",
      "status": "FAIL",
      "evidence": "Found 'MRP Rs. 20' — missing '(inclusive of all taxes)'",
      "fix": "Print as: Maximum Retail Price Rs. 20 (inclusive of all taxes)",
      "box": [1560, 940, 2240, 1010],
      "measurement": null
    },
    {
      "rule_id": "R8",
      "name": "Minimum numeral height",
      "citation": "Rule 7(2), 7(3) — LMPC (PC) Rules, 2011",
      "status": "FAIL",
      "evidence": "MRP numeral height measures 1.4 mm vs required 2.5 mm (PDP area ≈ 247 cm², class 100 < A < 500 cm²; σ = 0.07 mm — 3σ band well below the minimum)",
      "fix": "Increase MRP numeral height to at least 2.5 mm (PDP area class 100 < A < 500 cm²)",
      "box": [1560, 940, 2240, 1010],
      "measurement": { "measured_mm": 1.4, "sigma_mm": 0.07, "required_mm": 2.5, "pdp_area_cm2": 247.0, "area_uncertainty_cm2": 17.3, "pack_class": "100<A<500cm2", "method": "calibrated_photo" }
    }
  ],
  "artifacts": {
    "annotated_image": "outputs/SC-8F3K2_annotated.jpg",
    "report_pdf": "outputs/SC-8F3K2.pdf",
    "report_json": "outputs/SC-8F3K2.json",
    "report_csv": "outputs/SC-8F3K2.csv",
    "display_image": "outputs/SC-8F3K2_display.jpg"
  },
  "exemption": null,
  "error": null
}
```

### Field rules

- `scan_id`: `SC-` + 6 chars from `[A-Z0-9]` (no `0`/`O`/`1`/`I` to avoid lookalikes). Generated when the upload is requested; S3 upload key = `uploads/{scan_id}.{ext}`.
- `input.label_width_mm`: echo of the optional upload value (number in mm, or null) — the photographed object's width; drives R8 calibration on photos.
- `status`: `PENDING` → `PROCESSING` → `DONE | NEEDS_REVIEW | FAILED`. Terminal states never change again. (Approved additive transition: an abandoned upload can fail directly `PENDING` → `FAILED` — the upload-timeout family.)
- `extraction`: inline (the whole Extraction JSON lives inside the record — one read = the whole truth; this also makes benchmark evaluation trivial).
- `product`: populated from extraction after it succeeds; powers history search. `null` values allowed while status is `PENDING`/`PROCESSING`.
- `summary` + `results`: `null` while status is `PENDING`/`PROCESSING`.
- `exemption`: `null` unless the exemption layer fired (Feature 4, ENGINEERING.md). Shape: `{ "applied": bool, "citation": "Rule 26(a)", "reason": "..." }`. When `applied: true`, the scan ends in `DONE` with every result `NA` (reason `NA_EXEMPT`) and the summary counts exemptions separately from passes — an exempt scan must not render as a compliant scan. When the exemption is uncertain (tobacco proviso, >25 kg/L Rule 3 case), the scan ends in `NEEDS_REVIEW` and `exemption.reason` carries the explanation.
- `results[].rule_id`: `R1`–`R11` — exactly the 11 check IDs from DECISIONS.md §3. `name` and `citation` are defined there and must not drift.
- `results[].status`: `PASS | FAIL | NA | NEEDS_REVIEW`.
- `results[].fix`: `null` for PASS/NA; a concrete instruction for every FAIL.
- `results[].measurement`: only geometry checks (R8–R10) fill this; everything else `null`. R8 shape (locked — decision log 2026-09-18): `{ "measured_mm": 1.4, "sigma_mm": 0.07, "required_mm": 2.5, "pdp_area_cm2": 247.0, "area_uncertainty_cm2": 17.3, "pack_class": "100<A<500cm2", "method": "calibrated_photo" }` — `method` ∈ `calibrated_photo | pdf_exact`; `pack_class` ∈ `A<50cm2 | 50<A<100cm2 | 100<A<500cm2 | 500<A<2500cm2 | >2500cm2` (PDP-area classes — Rule 7 Table-I as substituted by GSR 629(E) 2018); `pdp_area_cm2` + `area_uncertainty_cm2` photo-only (`null` on `pdf_exact`). R9 carries the measured clear-space ratios, R10 the measured contrast ratio, each with `method`. Values are always measured quantities, never ratios against the requirement.
- `error`: `null` unless status is `FAILED` — then `{ "code": "...", "message": "..." }`. Scan-level codes: `OVERSIZED_FILE`, `STALE_PROCESSING`, `UPLOAD_TIMEOUT`, `EVENT_NOT_RECEIVED`, `EXTRACTION_FAILED`, `INTERNAL`.
- DynamoDB GSIs: GSI-1 (history — newest-first, paginated) and GSI-2 (brand search). Internal key attributes (`gsi1_pk`, `gsi1_sk`, `gsi2_pk`, `gsi2_sk`, `brand_key`, `product_key`, `failed_rules`) never appear in API responses. Artifacts are S3 keys, served via their public URLs.
- `summary.found_declarations`: count of the seven declaration fields that reached `VERIFIED` — the report's "found X of 7 declarations" line (Feature 6, ENGINEERING.md). Populated together with `summary`; `null` while `PENDING`/`PROCESSING`.
- `summary.exempt`: count of results with reason `NA_EXEMPT` — 0 on normal scans, 11 on exempt scans; counted separately from `pass` (an exempt scan never renders as compliant). Populated together with `summary` (additive — decision log 2026-09-17).
- Unanchored fields: `manufacturer_name`, `manufacturer_address`, `generic_name` carry no keyword anchor (ENGINEERING F1); UIs and the PDF report may render an "unanchored-verified" tag on these when verified — a static display hint, not a schema field (decision log 2026-09-18).
- `artifacts` is populated at the single terminal write; the whole object is `null` while `PENDING`/`PROCESSING`. `display_image` (Feature 6, ENGINEERING.md): public resized copy of the canonical processed image (max edge 1600 px, EXIF-stripped JPEG) — enables the UI's original/annotated toggle and interactive box overlay; generated with the other artifacts.

---

## 3. API surface (Lambda Function URL)

All responses are JSON unless the route says otherwise. Auth: none in MVP (stretch: Cognito).

### POST /upload

Request (JSON body):
```json
{ "filename": "bhujia_front.jpg", "content_type": "image/jpeg", "label_width_mm": 90 }
```

`label_width_mm` (optional, number > 0): the physical width in mm of the object as photographed — what fills the frame. Enables the font-size check (R8) on photos. Absent or null → R8 returns `NA` with reason `NO_SCALE_REFERENCE`; all other checks are unaffected.

Response `200`:
```json
{
  "scan_id": "SC-8F3K2",
  "upload_url": "https://labelcheck-uploads.s3.ap-south-1.amazonaws.com/...",
  "expires_in": 900
}
```

The client then does a single `PUT` to `upload_url` with the raw file bytes. S3 `ObjectCreated` triggers processing. Accepted `content_type`: `image/jpeg`, `image/png`, `application/pdf`. Anything else → `400`. Uploads are capped at 20 MB — an oversized file fails the scan with `OVERSIZED_FILE` (detected from the S3 event's size field).

### GET /scans/{scan_id}

Response `200`: the full Scan Record (section 2). `404` if unknown. The frontend polls this every ~2 s while `status` is `PENDING` or `PROCESSING`.

### GET /scans

Query params (all optional): `query` (fuzzy match on brand/product), `rule_id` (filter scans having this rule failed), `status`, `limit` (default 20, max 100), `last_key` (pagination cursor from the previous response).

Response `200`:
```json
{ "items": [ "...scan records (full shape)..." ], "last_key": "eyJzY2FuX2lkIjp7IlMiOiJTQy04RjNLMiJ9fQ==" }
```
`last_key` is `null` when there are no more pages. The cursor is opaque (base64-encoded by the backend) — pass it back verbatim.

### GET /stats

Response `200`:
```json
{
  "total_scans": 142,
  "overall": { "pass": 984, "fail": 311, "na": 121, "needs_review": 18 },
  "by_rule": {
    "R5": { "pass": 90, "fail": 52, "na": 0, "needs_review": 0 },
    "R8": { "pass": 61, "fail": 40, "na": 28, "needs_review": 13 }
  },
  "most_failed_rules": [ { "rule_id": "R5", "count": 52 }, { "rule_id": "R8", "count": 40 } ]
}
```
Keys of `by_rule` are exactly `R1`–`R11` (only rules with at least one scan appear).

### GET /reports/{scan_id}.{format}

`format` ∈ `pdf | json | csv`. A successful request returns `302` with a `Location` header pointing at the artifact's public S3 URL (the artifact's `Content-Type` was set at upload time). `404` if the scan hasn't finished. PDF and CSV are generated during processing; the JSON report is the Scan Record serialized.

### Error format (every route, every failure)

HTTP status + body:
```json
{ "error": { "code": "NOT_FOUND", "message": "Scan SC-XXXXXX does not exist" } }
```

Standard codes: `400` `BAD_REQUEST` (validation) · `404` `NOT_FOUND` · `405` `METHOD_NOT_ALLOWED` · `500` `INTERNAL` (with a short message; details go to CloudWatch, not the response).

---

## 4. Enums (single source)

| Enum | Values |
|---|---|
| scan status | `PENDING`, `PROCESSING`, `DONE`, `NEEDS_REVIEW`, `FAILED` |
| rule result status | `PASS`, `FAIL`, `NA`, `NEEDS_REVIEW` |
| source_type | `photo`, `pdf` |
| language | `en`, `hi`, `mixed`, `unknown` |
| net_quantity unit | `g`, `kg`, `ml`, `l`, `pcs` |

## 5. Fixtures

`fixtures/` holds golden Extraction JSONs and expected rule results per label, in this exact shape (locked — decision log 2026-09-18; benchmark labels are the same shape — one collection, two jobs, ENGINEERING F8 §8.5):

```json
{
  "input":  { "filename": "...", "content_type": "image/jpeg", "label_width_mm": 184.0 },
  "printed": {
    "manufacturer_name": { "raw": "..." }, "manufacturer_address": { "raw": "..." },
    "generic_name": { "raw": "..." },
    "net_quantity": { "raw": "Net Wt. 200 g", "parsed": { "value": 200, "unit": "g" } },
    "mfg_date": { "raw": "..." },
    "mrp": { "raw": "Maximum Retail Price Rs. 20 (inclusive of all taxes)" },
    "consumer_care": { "raw": "..." }, "brand_guess": "..."
  },
  "measured": {
    "pdp_area_cm2": { "value": 247.0, "uncertainty": 17.3 },
    "numeral_height_mm": { "mrp": { "value": 1.4, "uncertainty": 0.3 } }
  },
  "expected": { "R1": "PASS", "R5": "FAIL", "R8": "FAIL", "R11": "NA:DEPENDENCY_UNAVAILABLE" },
  "meta": { "language": "en", "path": "photo-calibrated", "strata": "R5-violation" }
}
```

Rules: `printed.*` is `null` when the field is genuinely not printed (the ground truth for ABSENT); `measured.uncertainty` feeds F8's ±0.3 mm R8 boundary exclusion and the class-interval rule (ENGINEERING F2 §2.5); `expected` values are `PASS | FAIL | NA:<reason-code> | NEEDS_REVIEW:<reason-code>`; `meta.path` ∈ `photo-calibrated | photo-uncalibrated | pdf`. A fixture that doesn't match this schema is invalid; `pytest` validates on load, and `benchmark/ground_truth.schema.json` (T8.5) is its machine-readable form.
