# /simulator/

- `DESIGN_NOTE.md` — the single most important document in the project.
  Specifies the composite kinetics model (B1 structure + B2/B3 six-group
  delayed-neutron kinetics + B4 Xe-135/I-135 coupling + B6/B8/B9 void
  calibration), with all parameters frozen and each one paired with a
  Validation Registry row. Must explicitly address the Keepin-1965 vs.
  RBMK-burnup delayed-neutron-fraction reconciliation (see
  `LIMITATIONS.md` Section 7).
- Source code and unit tests (tied to Validation Registry items V01–V03).
- `PLAUSIBILITY_REPORT.md` — output of Step 6, comparing simulator behavior
  against the Anchor Registry.
- Version tags / commit references used by `/data/DATASET.md`.
