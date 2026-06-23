"""
generate_dataset.py — Step 7: Synthetic dataset generation
============================================================
Produces a fully-labelled multivariate telemetry dataset for
training and evaluating the four DL anomaly-detection architectures.

Design decisions implemented here
----------------------------------
D8  : 10-channel telemetry (CH01-CH10)
D10 : outputs saved to Google Drive (large files outside git)
METRICS.md : train/val/test split = 70/15/15
DATASET.md : written alongside the data files

Anomaly taxonomy (6 classes)
------------------------------
0  normal               — baseline full-power operation
1  void_spike           — GT channel: CH03 / CH04
2  xenon_pit            — GT channel: CH05 / CH06 / CH07
3  rod_withdrawal       — GT channel: CH09
4  doppler_drift        — GT channel: CH08 / CH10
5  correlated_void_rod  — GT channel: CH03 (primary), CH09 (secondary)

Sensor corruption variants (applied as post-processing)
--------------------------------------------------------
Each physical scenario can optionally receive one of three sensor
corruptions, creating the "robustness to missing/irregular data"
engineering-axis test set (separate split, not mixed into train/val/test).

Output files
------------
{DRIVE_PROJECT}/datasets/
    train.npz       shape: (N_train, T, 10)  labels + metadata
    val.npz         shape: (N_val,   T, 10)
    test.npz        shape: (N_test,  T, 10)
    corruption.npz  shape: (N_corr,  T, 10)  robustness test set
    DATASET.md      documentation

Usage
-----
Run from Colab after Step 6. REPO_DIR and DRIVE_PROJECT must be set.
"""

import numpy as np
import os, sys, time, json
from datetime import datetime, timezone

# -- paths set by Colab environment (defined in setup cells) --
REPO_DIR      = os.environ.get("REPO_DIR",      "/content/Reactor_telemetry_NN")
DRIVE_PROJECT = os.environ.get("DRIVE_PROJECT",
                               "/content/drive/MyDrive/Reactor_Telemetry_NN")
DATASET_DIR   = f"{DRIVE_PROJECT}/datasets"
os.makedirs(DATASET_DIR, exist_ok=True)

sys.path.insert(0, f"{REPO_DIR}/simulator")
from rbmk_sim.simulator import Simulator
from rbmk_sim.scenarios import apply_sensor_corruption
from rbmk_sim.params    import N_CHANNELS, CHANNEL_NAMES


# ── Configuration ──────────────────────────────────────────────────────────

SEED_BASE     = 2024          # reproducibility root seed
DT            = 10.0          # seconds — output time step (matches simulator)
DURATION_STD  = 7200.0        # 2 h — standard scenario duration
DURATION_XE   = 36000.0       # 10 h — xenon pit (slow dynamics)

# Samples per class for train+val+test (before split)
N_PER_CLASS   = 500           # 500 × 6 classes = 3000 scenarios
SPLIT         = (0.70, 0.15, 0.15)   # train / val / test

# Corruption test set: N per (scenario_class × corruption_type)
N_CORRUPT_PER = 50            # 50 × 5 anomaly classes × 3 corruption types = 750

# Scenario durations
SCENARIO_DURATIONS = {
    "normal":              DURATION_STD,
    "void_spike":          DURATION_STD,
    "xenon_pit":           DURATION_XE,
    "rod_withdrawal":      DURATION_STD,
    "doppler_drift":       DURATION_STD,
    "correlated_void_rod": DURATION_STD,
}

# Class label mapping
LABEL_MAP = {
    "normal":              0,
    "void_spike":          1,
    "xenon_pit":           2,
    "rod_withdrawal":      3,
    "doppler_drift":       4,
    "correlated_void_rod": 5,
}

# Ground-truth channel per class (for interpretability validation, Step 11)
GT_CHANNEL_MAP = {
    "normal":              None,
    "void_spike":          "CH03",
    "xenon_pit":           "CH05",
    "rod_withdrawal":      "CH09",
    "doppler_drift":       "CH08",
    "correlated_void_rod": "CH03",
}

# Window length: number of time steps per sample
# Standard = 7200/10 + 1 = 721; xenon = 36000/10 + 1 = 3601
# We truncate/pad all sequences to T_WINDOW steps so all architectures
# receive the same input shape. Xenon sequences are downsampled to T_WINDOW.
T_WINDOW = 721   # ~ 2 h at 10 s resolution

CORRUPTION_TYPES  = ["dropout", "drift", "spike"]
# Corrupt the primary GT channel of each anomaly scenario
CORRUPT_CHANNELS  = {
    "void_spike":          "void_fraction",
    "xenon_pit":           "Xe",
    "rod_withdrawal":      "rho_rod_pcm",
    "doppler_drift":       "T_fuel",
    "correlated_void_rod": "void_fraction",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_window(X: np.ndarray, T: int) -> np.ndarray:
    """Resize time axis to T steps via slicing or linear interpolation."""
    if X.shape[0] == T:
        return X
    t_in  = np.linspace(0, 1, X.shape[0])
    t_out = np.linspace(0, 1, T)
    return np.column_stack(
        [np.interp(t_out, t_in, X[:, c]) for c in range(X.shape[1])]
    )


def generate_split(sim, rng_master, scenario_name, n_samples, seed_offset):
    """Generate n_samples runs of scenario_name, return (X, labels, gt_channels)."""
    duration = SCENARIO_DURATIONS[scenario_name]
    label    = LABEL_MAP[scenario_name]
    gt_ch    = GT_CHANNEL_MAP[scenario_name]
    X_list   = []

    for i in range(n_samples):
        seed = seed_offset + i
        result = sim.run_scenario(scenario_name, duration=duration, seed=seed)
        X = _to_window(result["telemetry"], T_WINDOW)
        X_list.append(X)

    X_arr = np.stack(X_list).astype(np.float32)   # (N, T, C)
    labels   = np.full(n_samples, label,  dtype=np.int8)
    gt_chs   = np.array([gt_ch or ""] * n_samples)
    return X_arr, labels, gt_chs


def generate_corruption_set(sim, scenarios, n_per, seed_offset):
    """
    For each anomaly scenario × corruption type, generate n_per samples
    with sensor-level corruption applied to the primary GT channel.
    Returns (X, labels, gt_channels, corruption_types).
    """
    X_list, lab_list, gt_list, ct_list = [], [], [], []
    rng = np.random.default_rng(seed_offset)

    for name in scenarios:
        duration = SCENARIO_DURATIONS[name]
        label    = LABEL_MAP[name]
        gt_ch    = GT_CHANNEL_MAP[name]
        raw_key  = CORRUPT_CHANNELS[name]

        for ctype in CORRUPTION_TYPES:
            for i in range(n_per):
                seed   = seed_offset + LABEL_MAP[name] * 10000 + \
                         CORRUPTION_TYPES.index(ctype) * 1000 + i
                result = sim.run_scenario(name, duration=duration, seed=seed)
                raw    = result["raw"]
                t_onset = duration * 0.4   # corrupt from 40% of run

                # Corruption kwargs
                kwargs = {}
                if ctype == "drift":
                    kwargs["rate"] = rng.uniform(0.001, 0.005)
                elif ctype == "spike":
                    kwargs["prob"]  = rng.uniform(0.02, 0.05)
                    kwargs["scale"] = float(0.1 * np.nanstd(raw[raw_key]))

                raw_c = apply_sensor_corruption(
                    raw, channel=raw_key, corruption_type=ctype,
                    t_onset=t_onset, rng=rng, **kwargs
                )
                # Rebuild telemetry from corrupted raw
                # Replace the affected physical channel in the telemetry array
                X = result["telemetry"].copy()
                # Map raw_key back to channel index
                key_to_col = {
                    "void_fraction": 2,   # CH03
                    "Xe":            5,   # CH06
                    "rho_rod_pcm":   8,   # CH09
                    "T_fuel":        7,   # CH08
                }
                if raw_key in key_to_col:
                    col = key_to_col[raw_key]
                    corrupted_sig = raw_c[raw_key]
                    if len(corrupted_sig) == X.shape[0]:
                        X[:, col] = corrupted_sig.astype(np.float32)

                X_w = _to_window(X, T_WINDOW)
                X_list.append(X_w)
                lab_list.append(label)
                gt_list.append(gt_ch or "")
                ct_list.append(ctype)

    return (np.stack(X_list).astype(np.float32),
            np.array(lab_list, dtype=np.int8),
            np.array(gt_list),
            np.array(ct_list))


# ── Main generation function ───────────────────────────────────────────────

def generate_all(verbose=True):
    sim = Simulator(dt=DT)
    t_start = time.time()

    all_X, all_labels, all_gt = [], [], []
    scenarios = list(LABEL_MAP.keys())

    if verbose:
        print(f"Generating {N_PER_CLASS} samples × {len(scenarios)} classes "
              f"= {N_PER_CLASS * len(scenarios)} scenarios")
        print(f"T_WINDOW={T_WINDOW} steps ({T_WINDOW * DT / 3600:.1f} h), "
              f"channels={N_CHANNELS}")
        print()

    for scenario_name in scenarios:
        seed_off = SEED_BASE + LABEL_MAP[scenario_name] * 10000
        X, labels, gt_chs = generate_split(
            sim, None, scenario_name, N_PER_CLASS, seed_off
        )
        all_X.append(X)
        all_labels.append(labels)
        all_gt.append(gt_chs)
        if verbose:
            print(f"  {scenario_name:25s}  {X.shape}  "
                  f"label={LABEL_MAP[scenario_name]}  "
                  f"gt={GT_CHANNEL_MAP[scenario_name]}")

    X_all      = np.concatenate(all_X,      axis=0)
    labels_all = np.concatenate(all_labels, axis=0)
    gt_all     = np.concatenate(all_gt,     axis=0)

    # Shuffle with fixed seed
    rng = np.random.default_rng(SEED_BASE)
    idx = rng.permutation(len(X_all))
    X_all      = X_all[idx]
    labels_all = labels_all[idx]
    gt_all     = gt_all[idx]

    # Train / val / test split
    N = len(X_all)
    n_train = int(N * SPLIT[0])
    n_val   = int(N * SPLIT[1])

    splits = {
        "train": (X_all[:n_train],        labels_all[:n_train],        gt_all[:n_train]),
        "val":   (X_all[n_train:n_train+n_val], labels_all[n_train:n_train+n_val],
                  gt_all[n_train:n_train+n_val]),
        "test":  (X_all[n_train+n_val:],  labels_all[n_train+n_val:],  gt_all[n_train+n_val:]),
    }

    if verbose:
        print()
        print("Split sizes:")
        for k, (X, y, _) in splits.items():
            anomaly_rate = (y > 0).mean()
            print(f"  {k:6s}  {X.shape}  "
                  f"anomaly_rate={anomaly_rate:.2%}")

    # Save splits
    for split_name, (X, y, gt) in splits.items():
        path = f"{DATASET_DIR}/{split_name}.npz"
        np.savez_compressed(path, X=X, y=y, gt_channel=gt,
                            channel_names=CHANNEL_NAMES)
        size_mb = os.path.getsize(path) / 1e6
        if verbose:
            print(f"  saved {path}  ({size_mb:.1f} MB)")

    # Corruption test set
    if verbose:
        print()
        print(f"Generating corruption test set "
              f"({N_CORRUPT_PER} × 5 anomaly classes × 3 types = "
              f"{N_CORRUPT_PER * 5 * 3} scenarios)")

    anomaly_scenarios = [s for s in scenarios if s != "normal"]
    X_c, y_c, gt_c, ct_c = generate_corruption_set(
        sim, anomaly_scenarios, N_CORRUPT_PER,
        seed_offset=SEED_BASE + 999999
    )
    path_c = f"{DATASET_DIR}/corruption.npz"
    np.savez_compressed(path_c, X=X_c, y=y_c, gt_channel=gt_c,
                        corruption_type=ct_c, channel_names=CHANNEL_NAMES)
    size_mb = os.path.getsize(path_c) / 1e6
    if verbose:
        print(f"  saved {path_c}  ({size_mb:.1f} MB)")

    elapsed = time.time() - t_start
    if verbose:
        print(f"\nTotal generation time: {elapsed:.1f} s")

    return splits, (X_c, y_c, gt_c, ct_c)


# ── DATASET.md ─────────────────────────────────────────────────────────────

def write_dataset_md(splits, corruption):
    X_tr, y_tr, _ = splits["train"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Class balance
    from collections import Counter
    def balance(y):
        c = Counter(y.tolist())
        inv = {v: k for k, v in LABEL_MAP.items()}
        return "  ".join(f"{inv[k]}={v}" for k, v in sorted(c.items()))

    md = f"""# DATASET.md — Synthetic Reactor Telemetry Dataset

## Generation metadata
- **Generated**: {now}
- **Simulator version**: commit in `simulator/` (see `git log`)
- **Generator script**: `data/generate_dataset.py`
- **Random seed base**: {SEED_BASE}
- **Time step (dt)**: {DT} s
- **Window length (T)**: {T_WINDOW} steps ({T_WINDOW * DT / 3600:.2f} h)

## Anomaly taxonomy

| Label | Scenario | Ground-truth driving variable | Duration |
|---|---|---|---|
| 0 | normal | — (no anomaly) | {DURATION_STD/3600:.0f} h |
| 1 | void_spike | CH03 (void_fraction), CH04 (rho_void) | {DURATION_STD/3600:.0f} h |
| 2 | xenon_pit | CH05 (rho_xenon), CH06 (Xe), CH07 (I) | {DURATION_XE/3600:.0f} h |
| 3 | rod_withdrawal | CH09 (rho_rod) | {DURATION_STD/3600:.0f} h |
| 4 | doppler_drift | CH08 (T_fuel), CH10 (rho_doppler) | {DURATION_STD/3600:.0f} h |
| 5 | correlated_void_rod | CH03 (primary), CH09 (secondary) | {DURATION_STD/3600:.0f} h |

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
| Train | train.npz | {len(splits['train'][0])} | {splits['train'][0].shape} | {(splits['train'][1]>0).mean():.1%} |
| Val | val.npz | {len(splits['val'][0])} | {splits['val'][0].shape} | {(splits['val'][1]>0).mean():.1%} |
| Test | test.npz | {len(splits['test'][0])} | {splits['test'][0].shape} | {(splits['test'][1]>0).mean():.1%} |
| Corruption | corruption.npz | {len(corruption[0])} | {corruption[0].shape} | 100% (anomaly only) |

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
"""
    path = f"{DATASET_DIR}/DATASET.md"
    with open(path, "w") as f:
        f.write(md)

    # Also copy to repo (DATASET.md is a doc artifact, not data)
    repo_path = f"{REPO_DIR}/data/DATASET.md"
    with open(repo_path, "w") as f:
        f.write(md)

    print(f"DATASET.md written to Drive and repo")


if __name__ == "__main__":
    splits, corruption = generate_all(verbose=True)
    write_dataset_md(splits, corruption)
    print("\nDataset generation complete.")
