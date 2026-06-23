"""
evaluator.py — Engineering-axis evaluation (Step 10)
======================================================
Implements all metrics from METRICS.md:
  Primary   : AUROC, AUPRC
  Secondary : latency, param count, GPU memory, training time
  Baselines : IsolationForest, PCA reconstruction
"""

import time, json, os
import numpy as np
import torch
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.ensemble import IsolationForest
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


# ── Anomaly scoring ───────────────────────────────────────────────────────

def compute_scores(model, X: torch.Tensor, device: str,
                   batch_size: int = 64) -> np.ndarray:
    """
    Run model.anomaly_score() on X in batches.
    Returns numpy array shape (N,).
    """
    model.eval()
    scores = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            x_b = X[i:i+batch_size].to(device)
            s   = model.anomaly_score(x_b)
            scores.append(s.cpu().numpy())
    return np.concatenate(scores)


# ── Detection threshold ───────────────────────────────────────────────────

def compute_threshold(scores_normal: np.ndarray,
                      percentile: float = 95.0) -> float:
    """
    Per METRICS.md: threshold = 95th percentile of normal-class val scores.
    """
    return float(np.percentile(scores_normal, percentile))


# ── Primary metrics ───────────────────────────────────────────────────────

def detection_metrics(
    scores: np.ndarray,
    y_true: np.ndarray,
) -> dict:
    """
    Compute AUROC and AUPRC.
    y_true: 0=normal, >0=anomaly (binary for metrics).
    """
    y_bin = (y_true > 0).astype(int)
    auroc = roc_auc_score(y_bin, scores)
    auprc = average_precision_score(y_bin, scores)
    return {"auroc": float(auroc), "auprc": float(auprc)}


# ── Secondary metrics ─────────────────────────────────────────────────────

def param_count(model: torch.nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def inference_latency_ms(model, x_single: torch.Tensor,
                          device: str, n_runs: int = 100) -> float:
    """
    Median inference latency in ms for a single sample (batch=1).
    Per METRICS.md: median of 100 runs.
    """
    model.eval()
    x = x_single.unsqueeze(0).to(device)
    times = []
    with torch.no_grad():
        # Warmup
        for _ in range(10):
            _ = model.anomaly_score(x)
        if device != "cpu" and torch.cuda.is_available():
            torch.cuda.synchronize()
        for _ in range(n_runs):
            t0 = time.perf_counter()
            _ = model.anomaly_score(x)
            if device != "cpu" and torch.cuda.is_available():
                torch.cuda.synchronize()
            times.append((time.perf_counter() - t0) * 1000)
    return float(np.median(times))


def estimate_flops(model, x_single: torch.Tensor, device: str) -> int:
    """
    Estimate FLOPs using torch profiler if available, else return -1.
    """
    try:
        from torch.profiler import profile, ProfilerActivity
        x = x_single.unsqueeze(0).to(device)
        with profile(activities=[ProfilerActivity.CPU],
                     with_flops=True) as prof:
            model.anomaly_score(x)
        total_flops = sum(
            e.flops for e in prof.key_averages() if e.flops > 0
        )
        return int(total_flops)
    except Exception:
        return -1


# ── Full engineering-axis evaluation ─────────────────────────────────────

def evaluate_architecture(
    model,
    arch_name: str,
    splits: dict,
    device: str,
    training_log_path: str,
    results_dir: str,
    seed: int = 0,
) -> dict:
    """
    Run full evaluation for one architecture.
    Returns a results dict; also saves to results_dir/{arch_name}_eval.json.
    """
    X_val, y_val, _  = splits["val"]
    X_test, y_test, gt_test = splits["test"]

    # Scores
    print(f"  [{arch_name}] Scoring val set...")
    val_scores   = compute_scores(model, X_val,  device)
    print(f"  [{arch_name}] Scoring test set...")
    test_scores  = compute_scores(model, X_test, device)

    # Threshold from normal-class val scores
    normal_mask  = (y_val == 0).numpy()
    threshold    = compute_threshold(val_scores[normal_mask])

    # Primary metrics
    metrics = detection_metrics(test_scores, y_test.numpy())

    # Per-class AUROC (one-vs-rest)
    class_names = ["normal", "void_spike", "xenon_pit",
                   "rod_withdrawal", "doppler_drift", "correlated_void_rod"]
    per_class = {}
    y_np = y_test.numpy()
    for ci, cname in enumerate(class_names[1:], start=1):
        mask = (y_np == 0) | (y_np == ci)
        if mask.sum() > 0:
            y_bin = (y_np[mask] == ci).astype(int)
            s_bin = test_scores[mask]
            if y_bin.sum() > 0:
                per_class[cname] = float(roc_auc_score(y_bin, s_bin))

    # Engineering metrics
    n_params = param_count(model)
    latency  = inference_latency_ms(model, X_test[0], device)
    flops    = estimate_flops(model, X_test[0], device)

    # GPU memory from training log
    gpu_mem_mb = 0.0
    if os.path.exists(training_log_path):
        with open(training_log_path) as f:
            tlog = json.load(f)
        gpu_mem_mb = max((e.get("gpu_mem_mb", 0)
                          for e in tlog.get("epochs", [])), default=0.0)
        total_training_time_s = tlog.get("total_time_s", 0.0)
        n_epochs_run = len(tlog.get("epochs", []))
        avg_epoch_time_s = (total_training_time_s / n_epochs_run
                            if n_epochs_run > 0 else 0.0)
    else:
        total_training_time_s = 0.0
        avg_epoch_time_s = 0.0

    result = {
        "arch":                 arch_name,
        "seed":                 seed,
        "auroc":                metrics["auroc"],
        "auprc":                metrics["auprc"],
        "auroc_per_class":      per_class,
        "threshold":            threshold,
        "param_count":          n_params,
        "latency_ms_median":    latency,
        "flops":                flops,
        "gpu_mem_mb":           gpu_mem_mb,
        "total_training_s":     total_training_time_s,
        "avg_epoch_time_s":     avg_epoch_time_s,
    }

    os.makedirs(results_dir, exist_ok=True)
    out_path = f"{results_dir}/{arch_name}_eval.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"  [{arch_name}] AUROC={metrics['auroc']:.4f}  "
          f"AUPRC={metrics['auprc']:.4f}  "
          f"params={n_params:,}  latency={latency:.2f}ms")
    print(f"  Eval saved: {out_path}")
    return result


# ── ML Baselines ──────────────────────────────────────────────────────────

def evaluate_baselines(splits: dict, results_dir: str) -> dict:
    """
    Train and evaluate Isolation Forest and PCA baselines.
    Per architecture_specs.md.
    """
    X_tr, y_tr, _ = splits["train"]
    X_te, y_te, _ = splits["test"]

    # Flatten (N, T, C) → (N, T*C)
    X_tr_flat = X_tr.numpy().reshape(len(X_tr), -1)
    X_te_flat = X_te.numpy().reshape(len(X_te), -1)
    y_te_np   = y_te.numpy()

    # PCA on normal-class train only (then project all)
    normal_mask = (y_tr.numpy() == 0)
    scaler = StandardScaler()
    X_tr_norm  = scaler.fit_transform(X_tr_flat[normal_mask])
    X_te_scaled = scaler.transform(X_te_flat)

    results = {}

    # ── PCA ──────────────────────────────────────────────────────────────
    print("  [pca] Fitting PCA (n_components=20)...")
    t0  = time.time()
    pca = PCA(n_components=20, random_state=42)
    pca.fit(X_tr_norm)
    X_te_pca   = pca.transform(X_te_scaled)
    X_te_recon = pca.inverse_transform(X_te_pca)
    pca_scores = np.mean((X_te_scaled - X_te_recon) ** 2, axis=1)
    pca_time   = time.time() - t0
    pca_metrics = detection_metrics(pca_scores, y_te_np)
    results["pca"] = {**pca_metrics, "fit_time_s": pca_time,
                       "param_count": 20 * X_tr_flat.shape[1]}
    print(f"  [pca] AUROC={pca_metrics['auroc']:.4f}  "
          f"AUPRC={pca_metrics['auprc']:.4f}")

    # ── Isolation Forest ──────────────────────────────────────────────────
    # First reduce with PCA to 50 components
    print("  [iforest] Fitting Isolation Forest...")
    pca50 = PCA(n_components=50, random_state=42)
    X_tr_pca50 = pca50.fit_transform(scaler.transform(X_tr_flat))
    X_te_pca50 = pca50.transform(X_te_scaled)

    t0 = time.time()
    iforest = IsolationForest(n_estimators=200, contamination=0.167,
                               random_state=42, n_jobs=-1)
    iforest.fit(X_tr_pca50)
    # IsolationForest returns negative scores; negate for anomaly direction
    if_scores = -iforest.score_samples(X_te_pca50)
    if_time   = time.time() - t0
    if_metrics = detection_metrics(if_scores, y_te_np)
    results["isolation_forest"] = {**if_metrics, "fit_time_s": if_time,
                                    "param_count": 0}
    print(f"  [iforest] AUROC={if_metrics['auroc']:.4f}  "
          f"AUPRC={if_metrics['auprc']:.4f}")

    os.makedirs(results_dir, exist_ok=True)
    path = f"{results_dir}/baselines_eval.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Baselines saved: {path}")
    return results


# ── Results summary table ─────────────────────────────────────────────────

def print_summary_table(all_results: dict):
    """Print a formatted engineering-axis comparison table."""
    header = (f"{'Architecture':<20} {'AUROC':>7} {'AUPRC':>7} "
              f"{'Params':>10} {'Latency(ms)':>12} {'TrainTime(s)':>13}")
    print("\n" + "=" * len(header))
    print("ENGINEERING-AXIS COMPARISON TABLE")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    order = ["lstm_ae", "gru_ed", "usad", "tf_ae",
             "isolation_forest", "pca"]
    for key in order:
        if key not in all_results:
            continue
        r = all_results[key]
        print(f"{key:<20} "
              f"{r.get('auroc', 0):>7.4f} "
              f"{r.get('auprc', 0):>7.4f} "
              f"{r.get('param_count', 0):>10,} "
              f"{r.get('latency_ms_median', 0):>12.2f} "
              f"{r.get('total_training_s', r.get('fit_time_s', 0)):>13.1f}")
    print("=" * len(header))
