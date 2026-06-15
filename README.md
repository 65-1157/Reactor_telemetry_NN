# Comparative DL Architectures for Multivariate Reactor Telemetry Anomaly Detection

**Interpretability Study with a Historical Case Illustration (Chernobyl)**

Target venue: IEEE Access (or an industrial-informatics-flavored IEEE venue).

## What this project is

A comparative, engineering-focused study of four deep learning architectures
(LSTM Autoencoder, GRU Encoder-Decoder, CNN/Wavelet-based, Transformer-based)
applied to **synthetic** multivariate reactor telemetry generated from a
literature-based RBMK-class kinetics simulator, evaluated on:

- detection performance (AUROC, AUPRC),
- engineering cost (training cost, inference latency, parameter count),
- robustness to missing/irregular data, and
- **interpretability**, validated by checking whether SHAP/attention outputs
  correctly attribute injected anomalies to their known, ground-truth driving
  variable.

A digitized Chernobyl pre-accident trajectory (from INSAG-7 / IAEA sources) is
used **only** as a qualitative, illustrative case study at the end of the
pipeline — never as training data, never as a calibration target for the
simulator, and never as the basis for any prevention or timing claim.

## Before you read anything else

Read [`LIMITATIONS.md`](LIMITATIONS.md). It is the living scope-constraint
document for the whole project and was drafted first, before any modeling.
Every other document and every line of code should be consistent with it.
[`CLAIMS_AUDIT.md`](CLAIMS_AUDIT.md) is the checklist used at the end of the
project to verify that nothing drifted outside these limits.

## Repository structure

| Path | Purpose |
|---|---|
| `/literature/` | Source Registry, Variable Registry, Anchor Registry, Validation Registry — the traceability backbone of the project. |
| `/simulator/` | Simulator Design Note, source code, unit tests, plausibility-check report, version tags. |
| `/data/` | Generated synthetic datasets, `DATASET.md`, generation scripts, seeds. |
| `/models/` | Architecture spec sheets (`/models/specs/`), training pipeline, `METRICS.md`, results (`/models/results/`). |
| `/interpretability/` | SHAP / attention extraction code and attribution-accuracy results. |
| `/case_study/` | Digitized Chernobyl data, provenance log, case-study figures and narrative. |
| `/paper/` | Manuscript source, figures, references. |
| `LIMITATIONS.md` | Scope-constraint document. Read first. |
| `CLAIMS_AUDIT.md` | Pre-submission claims checklist. |

## Roadmap

The full step-by-step roadmap (with locked decisions, registries, and
documentation requirements) is kept as a Word document for review purposes,
and is mirrored as plain text in [`ROADMAP.md`](ROADMAP.md) for easy diffing
in the repo.

## Current status

Step 1 (repository scaffolding) complete. Next: Step 2 — populate the four
registries in `/literature/`.
