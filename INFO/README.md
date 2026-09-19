# LabelCheck *(working name — final name is a DECISIONS.md §9 open item)*

A label photo or artwork PDF goes in, AI reads it (extraction only), a deterministic rule engine judges it against the 11 codified checks of the Legal Metrology (Packaged Commodities) Rules, 2011 — and an annotated compliance report card comes out: pass/fail/NA per rule, exact clause citations, violations highlighted on the label, fix-it guidance per violation.

Built for SIH 2026 (PS SIH26034, Ministry of Consumer Affairs) and the WeMakeDevs × AWS Bharat Builds Tour "First Commit" hackathon (Ship It track).

## Stack

S3 + Lambda + DynamoDB + Amazon Bedrock (ap-south-1, Mumbai) — exactly 4 AWS services. React frontend.

## Repo map

| Path | What |
|---|---|
| `DECISIONS.md` | The constitution — read this first |
| `AGENTS.md` | Rules for every AI coding agent and human contributor |
| `TASKS.md` / `PROGRESS.md` | The queue + live state |
| `CONTRACTS.md` | The ONLY shared document — the frontend builds against this and nothing else |
| `backend/` | The Lambda pipeline: extraction gauntlet, rule engine, geometry, reports, benchmark — specs in `backend/docs/` |
| `frontend/` | React app (builds against CONTRACTS.md only) |

## Core principle

The LLM reads the label; code judges it. The judge never hallucinates. Model quality may change coverage, never correctness — every verdict traces to deterministic verification (OCR crop-verify on pixels, or the PDF text layer). See `DECISIONS.md` §4.

## Status

Design complete (10 features proven in `backend/docs/ENGINEERING.md`), implementation starting. See `PROGRESS.md`.
