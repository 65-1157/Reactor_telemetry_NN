# METRICS.md — Frozen Evaluation Protocol
# Frozen before any model training (Step 9 / ROADMAP.md)
# Do NOT change after first training run without explicit logged justification.

## Primary metrics (detection performance)
- **AUROC** — Area Under the ROC Curve (primary ranking metric)
- **AUPRC** — Area Under the Precision-Recall Curve (primary for imbalanced classes)

## Secondary metrics (engineering axis)
- **Training time** — wall-clock seconds per epoch, averaged over all epochs
- **Inference latency** — wall-clock milliseconds per sample (batch=1), median of 100 runs
- **FLOPs** — floating-point operations per forward pass (estimated via thop or manual count)
- **Parameter count** — total trainable parameters (torch.numel)
- **GPU memory** — peak allocated memory during training (torch.cuda.max_memory_allocated)

## Interpretability metrics (Step 11)
- **Top-1 attribution accuracy** — fraction of test anomalies where the
  highest-attribution channel matches the ground-truth driving channel
- **Top-3 attribution accuracy** — fraction where gt_channel is in the
  top-3 attributed channels

## Reference platform (D10)
- **Primary**: NVIDIA T4 GPU (Colab), CUDA 11.x, PyTorch 2.x
- **Secondary**: CPU-only timing also recorded for reproducibility
- Python 3.10+, numpy 1.24+, scipy 1.10+
- Exact versions logged at training time in results/training_log.json

## Evaluation protocol
- **Scoring**: point-wise anomaly score = mean reconstruction error across channels
- **Protocol**: standard point-wise (NOT point-adjustment) to avoid known
  overestimation bias documented in the literature (e.g. Kim et al. 2022)
- **Threshold**: 95th percentile of normal-class reconstruction error on val set
- **Repetitions**: 5 independent runs per architecture (different random seeds)
- **Reported values**: mean ± std across 5 runs for all primary and secondary metrics

## Baselines (for context, not the paper's main contribution)
- **Isolation Forest** (sklearn) — classic anomaly detection baseline
- **PCA reconstruction** — linear reconstruction baseline
- Both evaluated on the same test set with the same threshold protocol

## Class balance note
Dataset is balanced: 500 samples per class × 6 classes = 3000 total.
Normal:anomaly ratio = 1:5 in raw data; train/val/test splits preserve this.
