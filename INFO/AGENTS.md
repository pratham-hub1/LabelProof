# AGENTS.md -- Agent Constitution for the LabelCheck Repo

**Who this is for:** every AI coding agent and human contributor touching this repository. Tooling per DECISIONS.md 8: IDE Antigravity; coding agent Gemini 3.1 Pro; debugging and user-perspective testing Nex 2.5 Pro -- both models get named in the hackathon writeup. Because the models are not Claude-level, **the documents carry the intelligence**: precise specs, TDD with fixtures, one task = one file + its tests.

---

## 1. The document hierarchy (read this before anything)

| Document | Authority | Rule for you |
|---|---|---|
| DECISIONS.md | THE source of truth | Every session starts by re-reading it. Every decision marked LOCKED is final -- changing it requires the whole team to agree plus a decision-log entry. Never delete or change anything in it without explicit owner approval; add/update only. If any other document or chat contradicts it, DECISIONS.md wins. |
| ENGINEERING.md | Proven designs (Features 1-10, all PROVEN) | Locked feature sections are frozen; changes only via an approved specific fix. Implementation directions are orders, not suggestions. |
| CONTRACTS.md | Frozen data contracts | Only approved additive changes are allowed (team decision + DECISIONS.md log entry + PROGRESS.md note). No agent may change this file. The frontend builds against ONLY this document. |
| backend/docs/CHECKS.md | Exact per-check spec | Compiled 1:1 from ENGINEERING decision tables. On any drift, ENGINEERING.md wins and CHECKS.md must be fixed. |
| backend/docs/ARCHITECTURE.md | Final system map | Backend-only reference; contains no decisions of its own. |
| PROGRESS.md | Live state | You update it after EVERY task. |
| TASKS.md | Queue | Take the next unblocked task from here. |

**Doc scoping (locked):** backend/docs/ARCHITECTURE.md, backend/docs/ENGINEERING.md and backend/docs/CHECKS.md are BACKEND build documents -- they must never lead to frontend code. CONTRACTS.md is the ONLY shared document; the frontend track has its own UI-focused doc if needed.

## 2. The proof-first rule

No feature or stage gets coded before its approach is written down AND mathematically justified (error sources, bounds, cost/latency budget) in ENGINEERING.md. All 10 features are already proven -- you translate proven designs into code; you NEVER make design decisions. **If you hit a case the documents do not cover: STOP and surface it to a human. Do not guess, do not interpret, do not decide.** Design correctness is proven by the math; implementation correctness is enforced by fixtures/TDD.

## 3. The core principle (governs every line you write)

Model-independent correctness: a weak model means more NA / NEEDS_REVIEW, NEVER a wrong verdict. The LLM reads the label; code judges it; the judge never hallucinates. If your code could ever emit a wrong verdict where an honest NA was available, the code is wrong.

## 4. Non-negotiable rules

1. **Repo history:** project code starts 17 Sept 2026 only -- the repo history must match the event window; prior work disqualifies the team. Planning/design docs are fine; code with earlier timestamps is not.
2. **4 AWS services only:** S3, Lambda, DynamoDB, Bedrock, region ap-south-1. NO API Gateway, no EventBridge/SNS/queues, no Cognito in the MVP. Adding a 5th service (e.g. Textract) is a team decision per DECISIONS.md 5 -- never yours to make.
3. **Config, not code:** pattern logic = code; pattern data = config. Nothing from the spec tables is hardcoded: `anchors.config`, `reasons.config`, `patterns.config`, `thresholds.config`, `tobacco.config`, `ingestion.config`, `reports.config`, `api.config`, `benchmark.config`.
4. **Determinism:** two runs of anything must give identical output. No wall-clock reads in report generation (timestamps come from record fields), no unseeded randomness, fixed encoder settings, reportlab invariant mode.
5. **State machine:** PENDING -> PROCESSING -> DONE | NEEDS_REVIEW | FAILED. Terminal states never change again. A FAIL is emitted only when (a) a mandatory declaration is confidently absent on a readable label, or (b) an explicit pattern matched on verified text. Both deterministic.
6. **Reason codes are first-class:** every NA / NEEDS_REVIEW carries one of the 9 reason codes plus a human-readable message and a suggested action (from config). Every FAIL carries a concrete fix.
7. **Pure functions:** every gate, check and measurement is a pure function in its own module, independently fixture-testable. No shared state, no ordering between checks. Two runs = identical output.
8. **LLM boundary:** no LLM output is trusted without passing the gauntlet (G1-G6). No check reads the LLM's confidence directly -- verdicts trace to field_status + patterns only. Bedrock is extraction only, Haiku-first with Sonnet fallback, behind one swappable interface.
9. **Deploy discipline:** ONE person owns Lambda deploys. Keys/credentials never in the repo or group chats -- they live in `~/.aws/credentials`.
10. **After every documentation write:** grep-verify across the docs for contradictions or leftovers before committing.

## 5. Workflow per task (every task, no exceptions)

1. Read TASKS.md; take the next unblocked task.
2. Re-read DECISIONS.md (always), the relevant feature section of ENGINEERING.md, and backend/docs/CHECKS.md for your task.
3. Write the one file + its tests. TDD: where the acceptance criteria name fixtures, write the fixtures first -- they are the answer key.
4. Run the verify commands (section 6). All green, determinism check passed.
5. Update PROGRESS.md: what was done, when, task ID, status.
6. A human reviews every task before merge. No exceptions.

## 6. Verify commands

- `pytest` -- the full suite: unit tests + golden fixtures. Fixture schemas are validated on load (a fixture that does not match CONTRACTS.md is invalid and fails loudly).
- `pytest -k determinism` -- the two-run identity assertions (rule engine, reports, benchmark).
- `python benchmark/run.py` (once the pipeline is live) -- run twice; the report bytes must be identical.
- After any doc edit: `grep -r "<pattern>" docs/` -- verify no contradictions or leftovers were introduced across DECISIONS.md / ENGINEERING.md / CONTRACTS.md / CHECKS.md.

## 7. When unsure

STOP and ask a human -- never guess. Ambiguity in the law or the spec resolves toward NEEDS_REVIEW in the product, and toward asking in your work. The three documents answer most questions; when they do not, the answer does not exist yet and must be created by a human decision, not by you.
