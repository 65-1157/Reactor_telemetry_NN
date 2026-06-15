# Roadmap (v1.0)

A Comparative Study of Deep Learning Architectures for Multivariate Reactor
Telemetry Anomaly Detection, with Interpretability Analysis on a Historical
Case Study.

Status: agreed working plan. Plain-text mirror of
`Reactor_Telemetry_AD_Roadmap_FINAL_v1.docx`. Supersedes earlier drafts.

## 1. Final Decisions (Locked)

Do not revisit without explicit discussion.

| Topic | Decision |
|---|---|
| Architectures | LSTM Autoencoder + GRU Encoder-Decoder + CNN/Wavelet-based + Transformer-based. All four retained. |
| GAT / Graph models | Removed entirely (was never implemented; closed off explicitly to avoid drift). |
| Historical figures as simulator parameter source | Rejected. |
| Historical figures for plausibility validation only | Adopted — central scientific safeguard. Do not weaken. |
| Simulator parameters | Sourced from B1–B9. Frozen before dataset generation; revisions require independent literature justification, logged. |
| Historical validation role | Supports Phase 2–3 (simulator plausibility checks) and Phase 9 (domain sanity check). Never used to fit/recalibrate parameters toward Chernobyl. |

### 1.1 Resulting Project Framing

- **Core contribution**: comparative, explainable anomaly detection for
  RBMK-inspired reactor telemetry across four DL architecture families,
  evaluated on engineering axes (cost, latency, parameters, robustness) plus
  interpretability.
- **Training/evaluation data**: entirely synthetic telemetry from a
  literature-based kinetics simulator (composite of B1–B9).
- **Historical Chernobyl data**: illustrative/qualitative only — never
  training data, calibration target, or basis for prevention/timing claims.
- **Interpretability claim**: cross-architecture validation of SHAP/attention
  outputs against known, injected ground-truth anomaly sources — the
  project's strongest contribution, not "first XAI on reactor telemetry".

## 2. Repository Structure

See top-level `README.md` for the folder table.

## 3. Literature & Validation Registries (`/literature/`)

Four registries (CSV): `source_registry.csv`, `variable_registry.csv`,
`anchor_registry.csv`, `validation_registry.csv`.

- **Source Registry**: source ID, citation, role, confidence. Seeded with
  A1–A11 (ML/interpretability literature) and B1–B9 (RBMK kinetics
  literature).
- **Variable Registry**: simulator variable, physical meaning, units,
  supporting source ID(s), reconciliation notes.
- **Anchor Registry — qualitative only**: historical facts about the
  Chernobyl sequence, used only for plausibility checks (Steps 6 and 4).
  **Firewall**: never transcribed as numeric targets/ranges/loss terms. If a
  plausibility check fails, fixes must cite an independent source from B1–B9
  — never "to match the historical trace".
- **Validation Registry**: generic RBMK/point-kinetics physics checks (V01–
  V04), independent of the Chernobyl case study. Seeded with:

| ID | Test | Expected behavior | Source |
|---|---|---|---|
| V01 | Xenon buildup after power increase | Delayed power recovery (iodine pit) | B4 |
| V02 | Positive void insertion | Positive power response | B8 |
| V03 | Control rod insertion (no positive-scram modeled) | Negative reactivity response | B2 |
| V04 | AZ-5 / positive-scram / graphite-displacer transient | NOT MODELED — explicit scope decision | LIMITATIONS.md §7 |

Additional rows added during Step 3 as the Simulator Design Note is drafted —
every frozen parameter should have a corresponding validation row before
simulator code is written.

## 4. Required Documentation Artifacts

### 4.1 Simulator Design Note (`/simulator/DESIGN_NOTE.md`)

The single most important artifact in the project. Specifies the composite
assembly: B1 (RBMK structure/xenon stability) + B2/B3 (six-group delayed-
neutron kinetics) + B4 (Xe-135/I-135 coupling) + B6/B8/B9 (void calibration).
Developed together with the Validation Registry: every frozen parameter is
paired with the validation test it must satisfy.

**Key cross-source consistency check (flag for Phase 9)**: B2/B3's six-group
precursor data follows the standard Keepin-1965 thermal-U-235 set, while RBMK
fuel with significant Pu-239/241 burnup has a measurably different effective
delayed-neutron fraction. The design note must state how this is reconciled
(e.g. adjusted beta value, with justification), not silently combined as-is.

### 4.2 DATASET.md (`/data/`)

Created before any model training: simulator version/commit, generation date
and seed(s), anomaly taxonomy (with ground-truth driving variable per
anomaly), class balance, variable list (cross-referenced to Variable
Registry), train/val/test split definition.

### 4.3 METRICS.md (`/models/`)

Frozen before any model is trained, not changed afterward without explicit
logged justification:

- Primary metrics: AUROC, AUPRC
- Secondary metrics: inference latency, FLOPs, memory — on a stated, fixed
  reference platform
- Interpretability metrics: Top-1 / Top-3 attribution accuracy against the
  ground-truth driving variable
- Evaluation protocol: explicit statement of scoring protocol (point-wise vs.
  point-adjustment), given known overestimation issues with naive
  point-adjustment protocols
- Repetition policy: number of runs/seeds per architecture, variance
  reporting (mean ± std)

### 4.4 Architecture Spec Sheets (`/models/specs/`)

One page per architecture (LSTM-AE, GRU encoder-decoder, CNN/Wavelet-based,
Transformer-based), each fixing: parameter count, input window length, loss
function, optimizer and LR strategy, reference platform for latency/memory
(must match METRICS.md). CNN/Wavelet arm: a single, named, citable published
variant — still open (Section 6).

## 5. Step-by-Step Roadmap

| Step | Title | Outcome |
|---|---|---|
| 1 | Repository scaffolding | Structured repo; LIMITATIONS.md and CLAIMS_AUDIT.md exist from day one. |
| 2 | Source/Variable/Anchor/Validation registries | Full traceability tables in `/literature/`. |
| 3 | Simulator Design Note + freeze | Frozen, reviewable spec; no simulator code yet. |
| 4 | Phase 9 sanity check (early) | Go/no-go on simulator design; changes logged with independent justification. |
| 5 | Simulator implementation | Working, versioned, tested simulator in `/simulator/`. |
| 6 | Plausibility check vs. historical anchors | `/simulator/PLAUSIBILITY_REPORT.md` confirming RBMK-class qualitative behavior. |
| 7 | Synthetic dataset generation | Versioned train/val/test datasets + `DATASET.md` in `/data/`. |
| 8 | Architecture specification freeze | Four frozen specs in `/models/specs/`, incl. CNN/Wavelet variant + reference platform. |
| 9 | Shared training pipeline + ML baselines + METRICS.md | Reproducible training infra; frozen evaluation protocol. |
| 10 | Train all architectures + baselines; engineering-axis evaluation | `/models/results/` — performance, cost, latency, params, robustness. |
| 11 | Interpretability layer + attribution validation | `/interpretability/` — Top-1/Top-3 attribution accuracy results. |
| 12 | Chernobyl digitization | Documented, versioned digitized dataset in `/case_study/`. |
| 13 | Case study application | `/case_study/` figures + narrative, qualitative only. |
| 14 | Internal claims audit | Signed-off `CLAIMS_AUDIT.md`. |
| 15 | Drafting + IEEE Access submission prep | Submission-ready manuscript + public repo. |

## 6. Remaining Open Items

None of these block earlier steps.

1. CNN/Wavelet architecture variant: collapse to one specific, citable
   published design before Step 8.
2. Reference hardware platform for latency/FLOPs/memory: fix before Step 8,
   consistent across all architectures and baselines.
3. Delayed-neutron precursor data reconciliation (Keepin-1965 vs. RBMK
   burnup-adjusted beta): resolve in the Simulator Design Note (Step 3),
   reviewed at Step 4.
4. B6/B7 accessibility for cross-validation in Steps 6/13: confirm access or
   substitute alternative sources from the Source Registry.
5. Evaluation protocol choice (point-wise vs. point-adjustment): fix in
   METRICS.md (Step 9).
6. Literature refresh pass close to submission (Step 15) — fast-moving 2025
   publications identified in the Track A review.
