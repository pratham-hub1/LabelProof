<div align="center">

# LabelProof

### LMPC 2011 label compliance in ~40 seconds. Photograph a product label, get a legally-cited compliance verdict with a full report.

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![AWS Lambda](https://img.shields.io/badge/AWS-Lambda-FF9900?logo=awslambda&logoColor=white)](https://aws.amazon.com/lambda/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-186%20passing-brightgreen)](./backend/tests)

**Built for the WeMakeDevs × AWS Bharat Builds Tour "First Commit" hackathon — Ship It track**

> 🟡 **Live Demo:** `<PLACEHOLDER — fill in your S3 website URL>` &nbsp;·&nbsp; [**Contracts**](./CONTRACTS.md) &nbsp;·&nbsp; [**Decisions**](./DECISIONS.md)

---

</div>

---

## Table of Contents

- [The Problem](#the-problem)
- [Core Safety Design](#core-safety-design)
- [How It Works](#how-it-works)
- [The 11 Compliance Rules](#the-11-compliance-rules)
- [Architecture](#architecture)
- [AWS Services](#aws-services)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [AWS Feedback](#aws-feedback-honest)
- [What We Learned](#what-we-learned)
- [Engineering Process](#engineering-process)
- [Team](#team)
- [Limitations & Roadmap](#limitations--roadmap)
- [License](#license)

---

## The Problem

Every pre-packaged product sold in India must carry **11 mandatory declarations** under the Legal Metrology (Packaged Commodities) Rules, 2011. Compliance verification today is manual: an inspector with a rulebook, eyeballing a label. That approach is:

- **Slow**: a multi-SKU audit takes hours
- **Error-prone**: geometric checks like numeral heights, clear space, and contrast are nearly impossible to do visually and consistently
- **Unscalable**: sellers cannot self-audit before committing to a print run of lakhs of labels; inspectors cannot scan thousands of SKUs at market speed

LabelProof automates the full 11-point checklist, including the *geometric* sub-rules that no prior tool handles, and returns a structured verdict in ~40 seconds.

---

## Core Safety Design

> **"Never a silent wrong verdict."**

A system that says *COMPLIANT* on a bad label is worse than no system at all. Every design decision in LabelProof traces back to one constraint: **ambiguous or unreadable data degrades to `NEEDS_REVIEW` for human review. It never silently produces a wrong verdict.**

### Anti-Hallucination by Construction

The LLM is the reader, not the judge. Its output passes a **six-gate verification gauntlet** before any verdict is issued:

| Gate | What it checks |
|------|----------------|
| **G0** | JSON schema validation. Malformed output is rejected immediately. |
| **G1** | Mandatory field presence. Every required field must be populated. |
| **G2** | Bounding-box sanity. Coordinates must be plausible for the image dimensions. |
| **G3** | Blur / readability. Severely blurred regions are flagged before OCR is attempted. |
| **G4** | OCR cross-verification. Tesseract crops each LLM-reported bounding box and verifies the extracted text against the LLM claim (normalized edit-distance = 0). |
| **G5** | Anchor verification. Key declarations are independently re-located. |
| **G6** | Per-field confidence gates (>=0.60). Low-confidence fields resolve to `NA` with a reason code, not to a verdict. |

Provider fallback is baked in at the infrastructure level as well (see [Architecture](#architecture)).

### Statistical Geometry Verdicts

Geometric checks (numeral height, clear space, contrast) use a **3-sigma rule** (sigma = 0.05 × measured height):

- `FAIL` only when a measurement is **confidently out of spec** (beyond 3-sigma below the minimum)
- `PASS` only when **confidently within spec** (beyond 3-sigma above the minimum)
- `NEEDS_REVIEW` for everything in between

Measurement uncertainty is carried through to the verdict rather than hidden.

---

## How It Works

```
User uploads label photo (or PDF) + physical label width (mm)
      |
      v
1. PREPROCESS    EXIF auto-rotate, PDF page-1 render @ 200 DPI (PyMuPDF)
      |
      v
2. EXTRACTION    Multimodal LLM reads the label (Gemini 3.1 Flash Lite,
                 OpenAI-compatible client, config-driven provider)
      |
      v
3. GAUNTLET      G0 schema -> G1 presence -> G2 box sanity -> G3 blur ->
                 G4 Tesseract OCR crop-verify -> G5 anchors -> G6 confidence
      |
      v
4. RULE ENGINE   R1-R11 checks + automatic small-pack exemptions +
                 geometric analysis (connected components, minAreaRect PCA,
                 delta-E contrast)
      |
      v
5. VERDICT + ARTIFACTS
      |
      +-- Overall: COMPLIANT / NON_COMPLIANT / NEEDS_REVIEW
      +-- 11-point report with legal citations, evidence, suggested fixes
      +-- PDF report (reportlab)
      +-- CSV + JSON data artifacts
      +-- Annotated & display images
```

---

## The 11 Compliance Rules

All rules codify the **Legal Metrology (Packaged Commodities) Rules, 2011**. Small packs (<=10 g or >25 kg) receive automatic `NA_EXEMPT` verdicts with the statutory citation.

| Rule | Declaration | Statutory Reference |
|------|-------------|---------------------|
| R1 | Manufacturer/packer name + complete address | Rule 6(1)(a), 10(1) |
| R2 | Common/generic name of commodity | Rule 6(1)(b) |
| R3 | Net quantity in correct unit | Rule 6(1)(c), 13 |
| R4 | Month & year of manufacture | Rule 6(1)(d) |
| R5 | MRP with prescribed wording | Rule 2(m), 6(1)(e) |
| R6 | Consumer care details | Rule 6(2) |
| R7 | Declarations in Hindi (Devanagari) or English | Rule 9(4) |
| R8 | Minimum numeral height (PDP-area based, GSR 629(E)) | Rule 7(2), 7(3) |
| R9 | Clear space around quantity declaration | Rule 8 |
| R10 | Contrast of MRP/quantity numerals | Rule 9(1)(b) |
| R11 | No misleading quantity qualifiers | Rule 12(6) |

Every `NA` and `NEEDS_REVIEW` verdict carries one of **9 reason codes** plus a human-readable message and a suggested action (sourced from `reasons.config`). Every `FAIL` carries a concrete fix.

---

## Architecture

```mermaid
flowchart TD
    subgraph Frontend["Frontend (S3 Static Site)"]
        A["React / Vite / TypeScript"]
    end

    subgraph API["API Layer"]
        B["Lambda Function URL\nREST API / AuthType NONE"]
    end

    subgraph Storage["Storage"]
        C["S3 uploads bucket"]
        J["S3 outputs bucket\npublic report artifacts"]
        K["DynamoDB\nscan lifecycle + GSI"]
    end

    subgraph Pipeline["Processing Pipeline (Lambda)"]
        D["Handler\nbackend/lambda/handler.py"]
        E["1. Preprocess\nEXIF transpose\nPDF to image at 200 DPI"]
        F["2. Extraction\nGemini 3.1 Flash Lite\nconfig-driven provider\nfallback: NVIDIA NIM"]
        G["3. Gauntlet G1-G6\nschema, presence, box sanity\nblur, OCR verify, confidence"]
        H["4. Rule Engine R1-R11\nexemptions + geometry\nPCA, delta-E contrast"]
        I["5. Verdict + Artifacts\nPDF, CSV, JSON\nannotated images"]
    end

    A -->|"POST /upload (presign request)"| B
    B -->|presigned S3 URL| A
    A -->|"PUT image/PDF direct to S3"| C
    C -->|S3 event trigger| D
    D --> E --> F --> G --> H --> I
    I -->|report artifacts| J
    I -->|state update| K
    J --> A
    K --> A
```

> **Provider agnosticism:** The extraction layer uses a single OpenAI-compatible client configured via `backend/config/llm_providers.config`. Switching providers requires zero code changes. The Bedrock-to-Gemini pivot during development was a config-only operation (see [AWS Feedback](#aws-feedback-honest)).

---

## AWS Services

| Service | Role | Notes |
|---------|------|-------|
| **S3 x3** | `uploads` (event-triggered intake), `outputs` (public report artifacts), `web` (static frontend hosting) | Event notification on `uploads` triggers the Lambda pipeline |
| **Lambda** | Entire backend: pipeline handler + REST API | Two layers attached: Tesseract OCR (eng + hin traineddata); slimmed Python deps layer (~170 MB unzipped) |
| **DynamoDB** | Scan lifecycle (`PENDING -> PROCESSING -> terminal`), GSI for scan history | Atomic conditional writes for retry-safety; DynamoDB Streams not used |
| **Lambda Function URL** | Public REST API | `AuthType NONE`; no API Gateway needed |
| **IAM** | Least-privilege inline policies per resource | |
| **CloudWatch** | Execution logs and debuggability | |

> **4 AWS core services: S3, Lambda, DynamoDB, Lambda Function URL.** No API Gateway, no EventBridge/SNS, no Cognito, no Textract in the MVP.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 |
| LLM (extraction) | Gemini 3.1 Flash Lite, multimodal, OpenAI-compatible endpoint |
| LLM fallback | NVIDIA NIM GLM-5.3-Flash (secondary provider) |
| OCR | Tesseract (eng + hin traineddata) |
| PDF rendering | PyMuPDF |
| Geometry / image | scipy, numpy, Pillow, OpenBLAS |
| Report generation | reportlab (deterministic / invariant mode) |
| AWS SDK | boto3 |
| Frontend | React 19, Vite 8, TypeScript, react-router-dom |
| Frontend hosting | S3 static website |

---

## Project Structure

```
LabelProof/
├── CONTRACTS.md              # Frozen API contract (backend + frontend build against this)
├── DECISIONS.md              # Constitution, read before anything else
├── AGENTS.md                 # Rules for every AI agent and contributor
├── TASKS.md / PROGRESS.md    # Work queue + live state
│
├── backend/
│   ├── lambda/
│   │   └── handler.py        # Lambda entry point
│   ├── src/
│   │   ├── preprocess/       # EXIF transpose, PDF render
│   │   ├── extraction/       # LLM client (provider-agnostic)
│   │   ├── gauntlet/         # Gates G1-G6
│   │   ├── rules/            # Checks R1-R11, engine, verdict, exemptions
│   │   ├── geometry/         # Connected components, PCA, delta-E contrast
│   │   ├── reports/          # PDF / CSV / JSON / image artifact generation
│   │   ├── ingestion/        # S3 event intake and presign API
│   │   ├── api/              # REST route handlers
│   │   └── pipeline/         # Orchestrator
│   ├── config/
│   │   ├── llm_providers.config   # Provider config (Gemini, NVIDIA NIM, Bedrock)
│   │   ├── anchors.config
│   │   ├── reasons.config
│   │   ├── patterns.config
│   │   ├── thresholds.config
│   │   ├── tobacco.config
│   │   ├── ingestion.config
│   │   ├── reports.config
│   │   ├── api.config
│   │   └── benchmark.config
│   ├── infra/
│   │   ├── lambda/           # deploy_lambda.py (creates role, function, trigger, URL)
│   │   ├── layers/           # Layer publish scripts
│   │   ├── buckets/          # S3 setup
│   │   ├── dynamodb/         # Table + GSI setup
│   │   └── bedrock/          # Bedrock policy (re-enable via config when available)
│   ├── docs/
│   │   ├── ENGINEERING.md    # Full feature specs (10 features, all proven)
│   │   ├── ARCHITECTURE.md   # System map
│   │   └── CHECKS.md         # Per-check spec (compiled 1:1 from ENGINEERING.md)
│   ├── tests/                # 186 automated tests
│   ├── fixtures/             # Golden fixture files
│   └── benchmark/            # Benchmark runner (framework built)
│
└── frontend/
    ├── src/                  # React app (builds against CONTRACTS.md only)
    └── vite.config.ts
```

> **Config, not code:** all rule pattern data, thresholds, reason codes, provider settings, and report parameters live in `backend/config/`. Nothing from the spec tables is hardcoded.

---

## Quick Start

### Prerequisites

- Python 3.12
- AWS credentials configured (`~/.aws/credentials`) with access to S3, Lambda, DynamoDB in `ap-south-1`
- A Gemini API key (primary provider)

### Local Development & Testing

```bash
# 1. Clone and set up the virtual environment
git clone <repo-url>
cd LabelProof
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Set required environment variables
set GEMINI_API_KEY=<your-key>
set TABLE_NAME=scans
set UPLOADS_BUCKET=<your-uploads-bucket>
set OUTPUTS_BUCKET=<your-outputs-bucket>
set WEB_BUCKET=<your-web-bucket>
set REGION=ap-south-1
set TESSDATA_PREFIX=<path-to-tessdata>

# 4. Run the test suite
pytest                         # full suite: unit + golden fixtures
pytest -k determinism          # two-run identity assertion
```

### Deploy to AWS

```bash
# Publish Lambda layers (Tesseract OCR + Python deps)
# See scripts in backend/infra/layers/

# Deploy the Lambda function (creates role, function, S3 trigger, Function URL)
python backend/infra/lambda/deploy_lambda.py

# Deploy frontend
cd frontend
npm install
npm run build
# Sync dist/ to S3 web bucket (see infra/buckets/)
```

### Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Primary LLM provider key | `AIza...` |
| `TABLE_NAME` | DynamoDB table name | `scans` |
| `UPLOADS_BUCKET` | S3 bucket for label uploads | `labelproof-uploads-...` |
| `OUTPUTS_BUCKET` | S3 bucket for report artifacts | `labelproof-outputs-...` |
| `WEB_BUCKET` | S3 bucket for static frontend | `labelproof-web-...` |
| `REGION` | AWS region | `ap-south-1` |
| `TESSDATA_PREFIX` | Path to Tesseract traineddata | `/opt/tessdata` |

---

## AWS Feedback (Honest)

This section responds to the hackathon's explicit ask for honest AWS platform feedback.

### What Worked Well

- **S3 event-driven intake**: the `s3:ObjectCreated` trigger to Lambda was instant and reliable throughout development and live burn-in with no configuration issues.
- **Lambda layers**: packaging Tesseract + traineddata as a separate layer kept the deployment workflow clean and the function zip small.
- **DynamoDB conditional writes**: `ConditionExpression` for state-machine transitions (e.g., `attribute_not_exists` / `status = PENDING`) worked exactly as documented. No retry races in production.
- **Lambda Function URL**: exposing a public REST API with `AuthType NONE` required zero additional service configuration. API Gateway was never needed.

### Friction 1: Bedrock Model Access in ap-south-1

Amazon Bedrock model access in `ap-south-1` surfaced a `ValidationException` caused by the distinction between base model IDs and cross-region inference profile ARNs. Because the extraction layer was built **provider-agnostic from day zero** (single OpenAI-compatible client, config-driven providers, G0 schema validation upstream of the provider call), we switched to Gemini via its OpenAI-compatible endpoint with **zero code changes**. The NVIDIA NIM fallback was configured as the secondary provider in the same operation. Bedrock can be re-enabled as a single config row in `backend/config/llm_providers.config` plus a small dialect adapter once in-region access is confirmed.

### Friction 2: Lambda Layer 250 MB Unzipped Limit

The `scipy + numpy + PyMuPDF + Pillow` stack exceeded the 250 MB unzipped limit (code + all layers combined). We pruned `scipy` to only the sub-packages the geometry code actually imports (`ndimage`, `special`, `linalg`) and removed the full OpenBLAS distribution, saving roughly 100 MB. The dependency graph is now documented so future additions can be evaluated against the budget before being added.

---

## What We Learned

None of us had shipped anything on S3, Lambda, or DynamoDB before this. A few things that genuinely surprised us:

**S3 events + Lambda is simpler than we thought it would be.** We went in assuming we'd need a queue between upload and processing. We didn't. The `s3:ObjectCreated` trigger just works, and once we added DynamoDB conditional writes to guard against Lambda retries processing the same label twice, the whole intake path became solid without any extra moving parts.

**The 250 MB Lambda layer limit is real and it bites.** We didn't think about transitive dependencies when we picked `scipy`. It dragged in a full OpenBLAS distribution we never called directly. We had to audit the actual import graph and strip it down to only the three subpackages the geometry code uses. Now that dependency graph is documented so it doesn't happen again.

**Building provider-agnostic from the start was the right call, but for a reason we didn't expect.** We designed the extraction layer to be swappable because it seemed like good practice. On day 3, Bedrock threw a `ValidationException` in `ap-south-1` over the difference between base model IDs and inference profile ARNs. Switching to Gemini took one config change. If the LLM client had been tightly coupled to Bedrock's API, that would have been a day of rewriting code instead.

**Frozen contracts between teams actually work.** Frontend and backend developed in parallel for most of the build with almost no coordination on the implementation. The contract document defined the shapes upfront and both sides built to it. When they connected, it worked. That's not something we expected to be true in a 4-day sprint.


## Engineering Process

### Spec-First Development

Every module was fully specified and peer-reviewed before any code was written. The frozen data contract ([`CONTRACTS.md`](./CONTRACTS.md)) was established at the start of the project and drove backend and frontend development in parallel. The frontend built against the contract document, not against backend code, which meant zero integration surprises when the two sides connected.

### Adversarial Cross-Model Review

An independent model reviewed the build in scenario mode: wrong-verdict construction attacks, contract diffs, failure-path audits, and edge-case enumeration. **20+ findings** were triaged and fixed before the live deployment.

### Test Coverage

- **186 automated tests**, all green
- **Deterministic pipeline**: identical inputs produce byte-identical reports across runs (replay-verified via `pytest -k determinism`)
- Fixture schemas are validated on load. A fixture that does not match `CONTRACTS.md` fails loudly.

### Live Validation

The pipeline was burn-in validated against a real label dataset before deployment.

---

## Team

| Member | Role | Contributions |
|--------|------|---------------|
| Pratham Soni | Backend & Architecture | Designed the serverless compliance pipeline including LLM extraction, OCR verification gauntlet, rule engine and geometry analysis. Owned the API layer and end-to-end integration. |
| Manav Solanki | AWS Infrastructure & DevOps | Built and maintained the AWS deployment: Lambda layers, S3/DynamoDB setup, IAM policies and the live production environment. |
| Prajyot Asawale | Frontend - UI & Experience | Owned the complete product interface: upload, scanning and results experience, visual design, and the report-viewing screens. |
| Alison Solanki | Frontend - API & Integration | Owned all API integration from the frozen `CONTRACTS.md`: upload/presign flow, polling, pagination and artifact delivery. Isolated and reported production endpoint issues during integration. |

---

## Limitations & Roadmap

### Current Limitations

| Area | Status |
|------|--------|
| Benchmark accuracy numbers | Framework is built; corpus collection and calibration is the next step. No accuracy percentage is claimed. |
| Non-upright label photos | Auto-orientation not yet implemented; safely degrades to `NEEDS_REVIEW` |
| Dot-matrix stamped dates | Hard for OCR to read reliably; flagged as `NEEDS_REVIEW`, never guessed |
| Free-tier LLM rate limits | Mitigated by the provider fallback chain; a paid tier removes this entirely |

### Roadmap

- [ ] Benchmark calibration on a collected label corpus (framework is production-ready)
- [ ] Auto-orientation for non-upright label photos
- [ ] Bedrock re-enable (config + dialect adapter once in-region access is confirmed)
- [ ] Mobile capture UX
- [ ] Batch scan support (multiple SKUs in one submission)

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [`DECISIONS.md`](./DECISIONS.md) | The constitution. Every locked design decision lives here. |
| [`CONTRACTS.md`](./CONTRACTS.md) | Frozen API contract. The only shared frontend/backend document. |
| [`backend/docs/ENGINEERING.md`](./backend/docs/ENGINEERING.md) | Full feature specs (10 features, all proven) |
| [`backend/docs/CHECKS.md`](./backend/docs/CHECKS.md) | Per-check spec, compiled 1:1 from ENGINEERING.md |

---

## License

This project is licensed under the MIT License. See the [`LICENSE`](./LICENSE) file for details.

---

<div align="center">

**LabelProof** &nbsp;·&nbsp; LMPC 2011 Compliance Automation &nbsp;·&nbsp; AWS ap-south-1

*Built at the WeMakeDevs × AWS Bharat Builds Tour "First Commit" Hackathon, September 2026*

</div>
