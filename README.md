# FinProof — Evidence-Driven Financial Control

> An AI-assisted, evidence-driven financial control system that reconciles multi-source transaction data, reconstructs financial event chains, verifies expected financial states, investigates discrepancies, and routes cases toward controlled resolution or human review.
---

## Overview

Financial reconciliation systems often answer only one question:

> **Do these numbers match?**

FinProof is designed to answer a harder sequence of questions:

> **What happened?**
> **Does the financial state make sense?**
> **If it does not, why?**
> **What evidence supports that conclusion?**
> **What should happen next?**

FinProof combines deterministic financial controls with an evidence-driven investigation and decision workflow.

The system processes financial records from multiple sources, builds relationships between them, reconstructs financial event chains, calculates expected financial states, detects discrepancies, investigates potential causes using controlled hypotheses, and applies deterministic decision policies to determine whether a case can be resolved automatically or requires human intervention.

The central design principle is:

> **AI is used for reasoning over financial evidence, while deterministic controls remain authoritative for financial correctness and final policy decisions.**

---

## Problem

Modern payment and financial systems generate related records across multiple systems:

- Orders
- Payments
- Refunds
- Fees
- Adjustments
- Settlements
- Bank transactions

These records do not always arrive in a clean one-to-one relationship.

A single business transaction may result in:

```text
Order
  ↓
Payment
  ↓
Refund
  ↓
Fee
  ↓
Settlement
  ↓
Bank Credit
```

There may also be:

- Partial refunds
- Split settlements
- Multiple related events
- Timing differences
- Missing records
- Duplicate records
- Incorrect amounts
- Ambiguous relationships
- Contradictory evidence

A simple comparison of two totals cannot explain these situations.

FinProof therefore treats reconciliation as an **evidence and control problem**, rather than only a matching problem.

---

## Core Idea

FinProof follows a seven-stage control pipeline:

```text
                 ┌──────────────────┐
                 │   Source Records  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │     Ingestion    │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Evidence Graph  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Reconciliation  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Reconstruction  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │   Verification   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │  Investigation   │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │     Decision     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Review / Audit   │
                 └──────────────────┘
```

The resulting control flow can be summarized as:

```text
Reconcile
    ↓
Reconstruct
    ↓
Verify
    ↓
Investigate
    ↓
Resolve / Escalate / Decide
```

---

## Key Design Principles

### 1. Deterministic Financial Correctness

Financial state calculations and control checks are deterministic.

The system does not rely on an AI model to decide whether a numerical financial invariant is satisfied.

For example:

```text
Expected Settlement
=
Payment
− Refunds
− Fees
− Adjustments
```

If the observed settlement differs from the expected state, the deterministic verification layer records the discrepancy.

### 2. Evidence Before Explanation

An explanation should not be accepted simply because it sounds plausible.

Investigation is constrained by available evidence and deterministic validation.

The intended reasoning flow is:

```text
Observed fact
      ↓
Evidence
      ↓
Hypothesis
      ↓
Validation
      ↓
Explanation
```

This prevents unsupported explanations from being treated as financial facts.

### 3. AI Is Not the Financial Authority

FinProof separates deterministic financial controls from the investigation layer.

**Deterministic controls** are responsible for:

- Financial state calculation
- Invariant checking
- Discrepancy detection
- Materiality
- Blocking conditions
- Decision policy

**Investigation layer** is responsible for:

- Exploring possible causes
- Organizing evidence
- Evaluating controlled hypotheses
- Producing an explanation that must be validated

This creates an explicit AI boundary:

```text
                 FINPROOF
                     │
          ┌──────────┴──────────┐
          │                     │
   DETERMINISTIC            INVESTIGATION
      CONTROL                  LAYER
          │                     │
          │                AI-assisted
          │                reasoning
          │                     │
          └──────────┬──────────┘
                     │
                     ▼
              CONTROLLED DECISION
```

---

## Architecture

```text
                         ┌─────────────────────┐
                         │    React Frontend   │
                         │ TypeScript + Vite   │
                         └──────────┬──────────┘
                                    │
                                    │ REST API
                                    ▼
                         ┌─────────────────────┐
                         │      FastAPI        │
                         │     API Layer       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Application Pipeline│
                         └──────────┬──────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          │                         │                         │
          ▼                         ▼                         ▼
   Ingestion Layer          Evidence Graph            Runtime State
          │                         │
          ▼                         ▼
   Reconciliation          Relationship Resolution
          │
          ▼
   Reconstruction
          │
          ▼
    Verification
          │
          ▼
   Investigation
          │
          ▼
     Decision
          │
          ▼
  Human Review / Audit
```

---

## Technology Stack

**Backend**

- Python
- FastAPI
- Pydantic
- Pytest

**Frontend**

- React
- TypeScript
- Vite
- CSS

**Architecture**

- Deterministic domain services
- In-memory runtime state
- Evidence graph representation
- REST APIs
- Reproducible synthetic data generation
- Controlled failure simulation

---

## End-to-End Pipeline

### Stage 1 — Ingestion

Source records are converted into the internal representations expected by the application.

Supported financial record categories include:

```text
Orders
Payments
Refunds
Fees
Adjustments
Settlements
Bank Transactions
```

The ingestion layer validates and normalizes source data before it reaches downstream control logic.

### Stage 2 — Evidence Graph

The ingested records are transformed into an evidence graph.

The graph represents relationships between financial events.

Conceptually:

```text
Order
  │
  └── Payment
        │
        ├── Refund
        │
        ├── Fee
        │
        └── Settlement
                 │
                 └── Bank Transaction
```

This representation allows FinProof to reason about relationships rather than treating every record as an isolated row.

### Stage 3 — Reconciliation

Reconciliation establishes relationships between related financial records.

The objective is not simply:

```text
payment.amount == settlement.amount
```

Instead, reconciliation considers the available evidence and relationships between records.

The result contains:

- Graph nodes
- Relationships
- Review items
- Reconciliation metrics

### Stage 4 — Reconstruction

Reconstruction converts related events into financial event chains.

For example:

```text
CASE_001
   │
   ├── ORDER
   ├── PAYMENT
   ├── REFUND
   ├── FEE
   └── SETTLEMENT
```

These chains provide the context required by the verification layer.

A reconstruction result contains:

- Event graph
- Event chains
- Chain states
- Batch-level reconstructed state

### Stage 5 — Verification

Verification is the authoritative financial-control layer.

It calculates an expected financial state and compares it with the observed state.

Important verification concepts include:

- Expected financial state
- Observed financial state
- Control checks
- Discrepancies
- Materiality
- Blocking conditions
- Affected events
- Supporting evidence

Verification statuses include:

```text
VERIFIED
PENDING
FAILED
INDETERMINATE
```

Control statuses include:

```text
PASS
FAIL
PENDING
NOT_APPLICABLE
```

---

## Financial Controls

FinProof evaluates financial invariants such as expected settlement relationships.

A simplified example:

```text
Payment
₹10,000

Refund
₹1,000

Fee
₹200

Expected Settlement
₹10,000 − ₹1,000 − ₹200

Expected Settlement
₹8,800
```

If the observed settlement is:

```text
₹9,300
```

then:

```text
Difference = ₹500
```

The verification layer records the discrepancy instead of attempting to explain it prematurely.

---

### Stage 6 — Investigation

Once a discrepancy has been detected, the system investigates potential causes.

The investigation workflow uses controlled hypotheses rather than unrestricted explanations.

Supported hypothesis categories include:

```text
REFUND
FEE
TAX
ADJUSTMENT
PARTIAL_SETTLEMENT
BUNDLED_SETTLEMENT
DUPLICATE_EVENT
TIMING_DIFFERENCE
MISSING_EVENT
SOURCE_DATA_ERROR
UNDETERMINED
```

Investigation statuses include:

```text
IN_PROGRESS
RESOLVED
UNRESOLVED
INSUFFICIENT_EVIDENCE
CONTRADICTION
```

The investigation layer is designed to be:

- Evidence-driven
- Read-only
- Deterministic in validation
- Provenance-aware
- Resistant to unsupported explanations

### Stage 7 — Decision

The decision layer converts verification and investigation results into controlled operational outcomes.

Possible outcomes include:

```text
AUTO_RESOLVED
PENDING
HUMAN_REVIEW
RESOLVED_WITH_APPROVAL
BLOCKED
```

The decision layer considers factors such as:

- Financial impact
- Materiality
- Evidence sufficiency
- Investigation validation
- Contradictory evidence
- Policy rules
- Approval requirements

The system does not treat a plausible explanation as sufficient justification for automatic resolution.

---

## Human Review

Cases requiring human intervention can be routed to a review workflow.

A reviewer can perform controlled actions such as:

```text
APPROVE
REJECT
REQUEST_MORE_EVIDENCE
```

A review may include:

- Reviewer ID
- Comment
- Previous decision
- Timestamp
- Resulting workflow state

This allows the system to demonstrate a complete human-in-the-loop control process.

---

## Audit Trail

FinProof records decision and review activity so that the system can answer:

> Who made the decision?
> What decision was made?
> Why was it made?
> What was the previous state?
> When did it happen?

The dashboard exposes:

- Decision audit history
- Review activity
- Pipeline processing history
- Stage durations

---

## Failure Simulation

FinProof includes a controlled failure-simulation framework for evaluating graceful degradation.

Supported failure modes include:

```text
NONE
AI_UNAVAILABLE
EVIDENCE_RETRIEVAL_FAILURE
MALFORMED_AI_OUTPUT
MISSING_ADJUSTMENT_SOURCE
DUPLICATE_BANK_RECORD
AMBIGUOUS_SETTLEMENT
```

The goal is not to make the system fail randomly.

Instead, failures are explicit and reproducible.

For example:

```text
AI_UNAVAILABLE
       │
       ▼
Verification completes
       │
       ▼
Investigation unavailable
       │
       ▼
No fabricated explanation
       │
       ▼
Controlled downstream handling
```

This allows the system to demonstrate an important operational property:

> **Failure of the investigation layer should not invalidate deterministic financial controls.**

---

## Reproducible Demo Scenarios

FinProof provides four high-level demo scenarios.

**NORMAL** — Represents internally consistent financial data.

```text
Expected state
      =
Observed state
```

The verification layer should produce a clean result.

**MIXED** — Introduces a controlled number of financial discrepancies.

The purpose is to demonstrate:

- Detection
- Discrepancy visualization
- Event-chain context
- Investigation
- Decision routing

**ADVERSARIAL** — Introduces larger controlled discrepancies.

This scenario is useful for demonstrating that material mismatches are surfaced rather than silently accepted.

**FAILURE_HEAVY** — Introduces a larger number of controlled settlement corruptions.

This scenario demonstrates behavior under a heavier discrepancy load.

---

## Reproducibility

Demo batches are generated using deterministic seeds.

A batch is defined by parameters such as:

```text
Scenario
Seed
Number of cases
```

This means the same configuration can reproduce the same demo dataset.

Example:

```text
Scenario: MIXED
Seed: 202
Cases: 100
```

This property is useful for:

- Debugging
- Benchmarking
- Demonstrations
- Research experiments
- Regression testing

---

## Benchmark Results

FinProof includes deterministic benchmark and evaluation results for the implemented control layers.

**Verification Benchmark**

```text
Total cases:                     100
Corrupted cases:                  30
Detected cases:                   30
Material discrepancy detection:  100%
False-pass rate:                   0%
False-fail rate:                   0%
```

These results represent the controlled benchmark configuration used during development.

**Investigation Benchmark**

```text
Investigation coverage:  100%
False explanations:        0
Validation rate:         100%
```

The evaluation also distinguished between fully and partially explained cases rather than treating every investigation as automatically resolved.

**Decision Benchmark**

```text
AUTO_RESOLVED:              60
PENDING:                    10
HUMAN_REVIEW:               25
BLOCKED:                     5
```

```text
False resolution rate:       0%
```

The decision layer also demonstrated a substantial reduction in cases requiring unrestricted manual investigation under the controlled benchmark.

---

## Testing

FinProof currently has a comprehensive automated test suite.

Current baseline:

```text
735 tests passed
```

The suite covers the implemented layers and workflows, including:

- Domain behavior
- Ingestion
- Evidence
- Reconciliation
- Reconstruction
- Verification
- Investigation
- Decision policy
- API behavior
- Runtime behavior
- Failure simulation

The project follows the principle:

> **New functionality must not silently regress previously validated control behavior.**

Run the complete test suite with:

```bash
pytest -q
```

Expected result for the current frozen baseline:

```text
735 passed
```

---

## API

The backend exposes REST endpoints through FastAPI.

Important endpoint groups include:

```text
POST /batches
POST /batches/{batch_id}/run
GET  /batches/{batch_id}

GET  /batches/{batch_id}/ingestion-report
GET  /batches/{batch_id}/reconstruction
GET  /batches/{batch_id}/verification

POST /batches/{batch_id}/reconcile
GET  /batches/{batch_id}/reconciliation

POST /batches/{batch_id}/verify

GET  /cases/{case_id}/decision
POST /cases/{case_id}/review
GET  /cases/{case_id}/audit
GET  /cases/{case_id}/review-package
```

The API surface may evolve as the project develops.

---

## Frontend Dashboard

The React dashboard provides an operational interface for the pipeline.

Major sections include:

```text
Overview
Cases
Investigations
Review Queue
Audit
Metrics
```

The dashboard provides visibility into:

- Batch status
- Pipeline progress
- Stage timings
- Verification status
- Financial impact
- Discrepancies
- Event chains
- Investigation traces
- Review queue
- Decision audit history
- Operational metrics
- Benchmark metrics

---

## Operational vs Benchmark Metrics

FinProof deliberately separates operational metrics from benchmark metrics.

**Operational Metrics** describe the current execution:

- Pipeline duration
- Stage durations
- Records processed
- Current case counts
- Current financial impact
- Current control status

**Benchmark Metrics** describe controlled evaluation experiments:

- Detection rate
- False-pass rate
- False-fail rate
- Investigation coverage
- False explanation rate
- Decision outcomes

This separation prevents benchmark results from being presented as if they were live production measurements.

---

## Setup

### Requirements

Recommended environment:

```text
Python 3.x
Node.js
npm
```

### Backend Setup

Create and activate a virtual environment.

**Windows**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

Run the API:

```powershell
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

FastAPI also provides its interactive development documentation through the standard documentation endpoints.

### Frontend Setup

Move into the frontend directory:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend is configured to communicate with the FastAPI backend through the Vite development proxy.

The default frontend development server runs on:

```text
http://localhost:5173
```

---

## Running the Full Demo

Start the backend:

```powershell
uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd frontend
npm run dev
```

Then open the frontend dashboard.

A typical demonstration flow is:

```text
1. Select a scenario
2. Create a batch
3. Run the pipeline
4. Observe stage progress
5. Inspect verification controls
6. Open a discrepancy
7. Inspect the reconstructed event chain
8. Review investigation information
9. Inspect the decision
10. Route a case to human review when applicable
11. Record a review action
12. Inspect the audit history
13. Compare operational and benchmark metrics
14. Demonstrate controlled failure behavior
```

---

## Research Direction

FinProof is designed as more than a conventional CRUD application.

The research direction centers on the question:

> **Can financial reconciliation be made more reliable by combining deterministic financial controls, structured evidence, controlled investigation, and policy-based decision making?**

Potential research dimensions include:

**Detection** — How reliably can financial discrepancies be detected under controlled corruption?

**Evidence Quality** — How does the availability or contradiction of evidence affect explanation quality?

**Investigation Safety** — Can investigation systems be constrained so that unsupported explanations are rejected?

**Decision Automation** — Under what conditions can financial cases be safely auto-resolved?

**Human Intervention** — Can evidence-driven investigation reduce unnecessary manual investigation while preserving conservative escalation?

**Failure Resilience** — What happens when an investigation or AI subsystem becomes unavailable?

**Reproducibility** — Can financial-control experiments be reproduced using deterministic scenarios and seeds?

---

## AI Safety Boundary

FinProof deliberately uses AI where reasoning over financial evidence adds value, while keeping financial correctness deterministic and auditable.

The intended boundary is:

```text
                 RAW FINANCIAL DATA
                         │
                         ▼
                DETERMINISTIC CONTROL
                         │
                         ▼
                VERIFIED FINANCIAL STATE
                         │
                         ▼
                 INVESTIGATION LAYER
                         │
                  ┌──────┴──────┐
                  │             │
               Evidence       Hypotheses
                  │             │
                  └──────┬──────┘
                         │
                         ▼
                DETERMINISTIC VALIDATION
                         │
                         ▼
                   DECISION POLICY
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
        Auto-resolve   Pending   Human Review
```

The system is designed so that:

- AI cannot change source financial records
- AI cannot redefine financial invariants
- Unsupported explanations are not treated as facts
- Contradictory evidence can block resolution
- Insufficient evidence can prevent automatic resolution
- AI/investigation failure can be represented explicitly
- Human review remains available for uncertain cases

---

## Limitations

FinProof is currently a research and engineering prototype.

**Synthetic Data** — The current demonstration and benchmark environment relies on reproducible generated financial records rather than production financial datasets.

**In-Memory Runtime** — Batch state is currently maintained in memory during application execution. Restarting the backend removes the current runtime state.

**Controlled Scenarios** — The demo scenarios intentionally inject known classes of discrepancies. They are designed for reproducibility and evaluation rather than to represent the full distribution of production financial failures.

**Limited Failure Injection** — The failure simulation framework currently provides a controlled set of failure modes. It is not a complete model of every infrastructure or AI failure.

**Research Evaluation** — Benchmark results are based on controlled evaluation configurations and should not be interpreted as production guarantees.

---

## Project Status

FinProof has completed its major implementation phases and is now in the stabilization and evaluation stage.

Current focus:

```text
Build
  ↓
Validate
  ↓
Measure
  ↓
Document
  ↓
Research
```

The core implementation is intentionally being frozen to prioritize:

- Reproducibility
- Regression safety
- Benchmark validation
- Documentation
- Research evaluation
- Final demonstration quality

---

## Development Philosophy

FinProof follows several principles.

**Don't automate uncertainty blindly.** If evidence is insufficient, the system should preserve uncertainty.

**Don't let plausible explanations become financial truth.** Explanations must be supported and validated.

**Don't hide failures.** Infrastructure and investigation failures should be visible and controlled.

**Don't confuse benchmark performance with production performance.** Evaluation metrics and live operational metrics are separated.

**Don't sacrifice deterministic controls for AI convenience.** The financial control layer remains authoritative.

---

## Future Work

Possible future extensions include:

- Persistent database-backed runtime state
- Production payment-provider integrations
- Larger real-world datasets
- More sophisticated evidence retrieval
- Advanced graph analytics
- Additional failure-injection experiments
- Interactive event-graph exploration
- Larger-scale performance evaluation
- Formal comparison against traditional reconciliation approaches
- Human-review effectiveness studies
- More extensive explainability evaluation

These are intentionally outside the current frozen implementation scope.

---

## Contributing

This project is currently maintained as an academic/research project.

Before making changes:

1. Run the existing test suite.
2. Understand which pipeline phase the change affects.
3. Avoid modifying deterministic financial controls without corresponding tests.
4. Add regression tests for new behavior.
5. Keep benchmark metrics reproducible.
6. Preserve the separation between operational metrics and benchmark results.

Run:

```bash
pytest -q
```

before submitting changes.

---

## License

This project was built for the Razorpay AI Buildathon and is intended for hackathon evaluation and demonstration purposes.

---

## Authors

**Amisha Malhotra**
Graphic Era University

---

## Final Summary

FinProof is an evidence-driven financial control platform designed around a simple principle:

> **Don't just tell me that the numbers are wrong. Show me what happened, prove why it is wrong, explain what the evidence supports, and control what happens next.**

The system combines:

```text
Multi-source financial data
          ↓
Evidence graph
          ↓
Reconciliation
          ↓
Financial reconstruction
          ↓
Deterministic verification
          ↓
Evidence-driven investigation
          ↓
Policy-based decision
          ↓
Human review
          ↓
Audit trail
```

with reproducible scenarios, controlled failure simulation, automated testing, and measurable benchmark evaluation.

**FinProof — Reconcile. Reconstruct. Verify. Investigate. Decide.**
