# DATASET.md — Synthetic Reactor Telemetry Dataset

## Generation metadata
- **Generated**: 2026-06-23 19:22 UTC
- **Simulator version**: commit in `simulator/` (see `git log`)
- **Generator script**: `data/generate_dataset.py`
- **Random seed base**: 2024
- **Time step (dt)**: 10.0 s
- **Window length (T)**: 721 steps (2.00 h)

## Anomaly taxonomy

| Label | Scenario | Ground-truth driving variable | Duration |
|---|---|---|---|
| 0 | normal | — (no anomaly) | 2 h |
| 1 | void_spike | CH03 (void_fraction), CH04 (rho_void) | 2 h |
| 2 | xenon_pit | CH05 (rho_xenon), CH06 (Xe), CH07 (I) | 10 h |
| 3 | rod_withdrawal | CH09 (rho_rod) | 2 h |
| 4 | doppler_drift | CH08 (T_fuel), CH10 (rho_doppler) | 2 h |
| 5 | correlated_void_rod | CH03 (primary), CH09 (secondary) | 2 h |

## Channel list (D8)

| Index | Channel | Physical meaning | Units |
|---|---|---|---|
| 0 | CH01 | Normalised reactor power | dimensionless |
| 1 | CH02 | Total reactivity | pcm |
| 2 | CH03 | Void fraction | fraction [0,1] |
| 3 | CH04 | Void reactivity | pcm |
| 4 | CH05 | Xenon reactivity | pcm |
| 5 | CH06 | Xe-135 concentration (norm) | dimensionless |
| 6 | CH07 | I-135 concentration (norm) | dimensionless |
| 7 | CH08 | Fuel temperature | K |
| 8 | CH09 | Rod reactivity | pcm |
| 9 | CH10 | Doppler reactivity | pcm |

## Dataset splits

| Split | File | Samples | Shape | Anomaly rate |
|---|---|---|---|---|
| Train | train.npz | 2100 | (2100, 721, 10) | 84.7% |
| Val | val.npz | 450 | (450, 721, 10) | 80.4% |
| Test | test.npz | 450 | (450, 721, 10) | 79.8% |
| Corruption | corruption.npz | 750 | (750, 721, 10) | 100% (anomaly only) |

## Corruption test set

Applied to anomaly scenarios only. Corrupts the primary GT channel.

| Type | Description | Purpose |
|---|---|---|
| dropout | Signal replaced with NaN from t_onset | Missing sensor |
| drift | Linear additive bias from t_onset | Sensor calibration drift |
| spike | Random impulse noise from t_onset | Electrical interference |

t_onset = 40% of scenario duration in each case.

## Sim-to-real gap (per LIMITATIONS.md)

Strong performance on this synthetic dataset is **not** evidence of
performance on real plant telemetry. The dataset is generated from a
point-kinetics model with deliberate simplifications (lumped thermal
hydraulics, single-node fuel temperature, 1D no-spatial effects).
This limitation is stated explicitly in LIMITATIONS.md Section 2
and must appear in the paper's limitations section.
