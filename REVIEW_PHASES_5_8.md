# ADVERSARIAL REVIEW: PHASES 5-8

## S1 — SILENT WRONG VERDICT
* **B1** (`backend/src/geometry/calibrate.py`, line 42)
  * **Why**: `min_area_rect` computes `width` unconditionally as the larger of the two PCA extents (`max(extent1, extent2)`). For portrait-oriented labels (where height > width), this incorrectly assigns the label's physical height to the `w_px` variable. The scale factor (`scale = w_px / label_width_mm`) will thus be incorrectly high, causing `height_mm` in R8 checks to be artificially tiny. This triggers a confident FALSE FAIL, violating the "never a wrong FAIL" guarantee.
  * **Fix**: The function should return both extents and use `label_width_mm` (or user-provided orientation) to determine which extent correctly corresponds to the physical width.

## S2 — STATE LIE
* **B2** (`backend/lambda/handler.py`, line 152)
  * **Why**: In the `run_pipeline` try/except block, if the pipeline crashes AFTER `generate_and_upload_artifacts` successfully writes all 5 artifacts to public S3, but BEFORE or DURING the success `mark_terminal` call, the `except` block catches the exception and calls `mark_terminal(status='FAILED')`. The DynamoDB state correctly reflects `FAILED`, but the 5 artifacts (including passing/failing annotated images) are already leaked to the `outputs_bucket` and exist forever. This is a partial write where a failed run leaves success-like artifacts publicly accessible.
  * **Fix**: Artifact upload should only happen AFTER the `mark_terminal` conditional write succeeds, or artifacts must be explicitly cleaned up/deleted in the `except` block.

## S3 — CONTRACT VIOLATION
* **B3** (`backend/src/pipeline/artifacts.py`, lines 85, 110)
  * **Why**: The `artifacts` dictionary is constructed using keys `annotated`, `display`, `report`, `data`, `record` with values as `s3://` URIs. `CONTRACTS.md` specifies keys `annotated_image`, `display_image`, `report_pdf`, `report_csv`, `report_json` with values as S3 keys (e.g., `outputs/SC-...jpg`). `api/reports.py` also mistakenly expects the incorrect keys. This completely breaks the API contract and frontend expectations.
  * **Fix**: Update the `artifacts` dictionary keys and values in `artifacts.py` to match the exact string formats specified in `CONTRACTS.md`.
* **B4** (`backend/src/ingestion/upload.py`, lines 48-51)
  * **Why**: `create_pending_record` omits the `artifacts`, `exemption`, and `extraction` fields entirely. `CONTRACTS.md` requires "Every field key always exists in the JSON" and explicitly states these fields must be `null` while `PENDING/PROCESSING`. `serialize.py` silently drops these missing fields, causing the API to return incomplete JSON during polling.
  * **Fix**: Initialize `artifacts`, `exemption`, and `extraction` with `{'NULL': True}` in `create_pending_record`.
* **B5** (`backend/src/api/stats.py`, line 81)
  * **Why**: `most_failed_rules` returns a flat list of rule IDs (e.g., `["R5", "R8"]`), but `CONTRACTS.md` requires a list of objects (`[{"rule_id": "R5", "count": 52}]`).
  * **Fix**: Return the list of dictionaries directly from `rule_fail_counts`.

## S4 — DEAD END
* **B6** (`backend/src/api/get_scan.py`, line 36)
  * **Why**: When a scan is in the `PENDING` state, `get_scan` attempts to call `reap_stale_pending(table.name, item)`. However, `reap_stale_pending` in `reapers.py` requires three positional arguments: `table_name`, `item`, and `bucket_name`. The missing `bucket_name` argument causes a `TypeError`, returning a 500 internal server error. The frontend will never be able to poll a `PENDING` scan, resulting in an unrecoverable dead end for the client loop.
  * **Fix**: Pass `os.environ.get('UPLOADS_BUCKET')` as the third argument to `reap_stale_pending` in `get_scan.py`.

## S5 — DEPLOYED-PATH DIVERGENCE
* **B7** (`backend/src/extraction/client.py`, lines 77-78)
  * **Why**: The default Bedrock model IDs are `anthropic.claude-3-5-haiku-20241022-v1:0` and `anthropic.claude-sonnet-4-20250514-v1:0`. On real AWS in `ap-south-1`, standard Claude 3.5 Haiku/Sonnet is not available natively and requires a cross-region inference profile ID (e.g., `us.anthropic.claude...`). These hardcoded base model IDs will fail in production in the target region.
  * **Fix**: Use cross-region inference profile IDs for the default models in `ap-south-1`.
* **B8** (`backend/src/ingestion/presign.py`, line 15)
  * **Why**: The Lambda generates a presigned PUT URL using `put_object`. On real AWS, the Lambda's execution role MUST have `s3:PutObject` permission on the uploads bucket for the client to successfully use this URL, even though the Lambda itself never uploads to that bucket directly. (Moto mocks typically ignore IAM validation for presigning).
  * **Fix**: Ensure the IAM role explicitly grants `s3:PutObject` to the `labelcheck-uploads` bucket.

## S6 — RETRY SAFETY
* No critical findings. `claim_scan` safely handles repeated concurrent pipeline execution with atomic `PROCESSING` test-and-set. Sequential retries of the same file to the same upload URL correctly skip double processing.

## OWNER QUESTIONS
1. **Mocked Pipeline**: `backend/src/pipeline/main.py`'s `run_pipeline` function returns hardcoded dummy results (`"R1": {"status": "PASS"}`) and bypasses the actual verification gauntlet, LLM extraction, and rule engine. Is this a temporary stub designed to unblock Phase 5-8 testing, and should it be wired up before the final run?
