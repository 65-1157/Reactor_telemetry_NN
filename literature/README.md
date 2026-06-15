# /literature/

Traceability backbone of the project. Four registries, each as a CSV (or
Markdown table) — populated in Step 2:

- `source_registry.csv` — every cited source (A1–A11, B1–B9), its role
  (training-data simulator component / calibration / cross-validation /
  background), and a confidence level.
- `variable_registry.csv` — every simulator variable, its physical meaning,
  units, and supporting source ID(s).
- `anchor_registry.csv` — **qualitative only** historical facts about the
  Chernobyl pre-accident sequence, used solely for plausibility checks
  (Steps 6 and 4/Phase 9). See `LIMITATIONS.md` Section 3 before editing this
  file.
- `validation_registry.csv` — generic RBMK/point-kinetics physics checks the
  simulator must pass (e.g. V01–V04), independent of the Chernobyl case
  study. Every frozen simulator parameter should map to at least one row
  here before simulator code is written.
