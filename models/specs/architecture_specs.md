# Architecture Specification Sheets (Step 8 / D8–D9)
# All specs frozen before implementation.
# Reference platform: NVIDIA T4 GPU, PyTorch 2.x (D10)

---

## ARCH-1: LSTM Autoencoder (LSTM-AE)

**Citation**: Based on the LSTM-AE pattern established in
Malhotra et al. (2016) "LSTM-based Encoder-Decoder for Multi-sensor
Anomaly Detection", ICML Anomaly Detection Workshop.
Also consistent with A4 in Source Registry (PMC, 2020).

| Parameter | Value |
|---|---|
| Input window | 721 time steps × 10 channels |
| Encoder | 2-layer LSTM, hidden=64, dropout=0.1 |
| Latent | Last hidden state, dim=64 |
| Decoder | 2-layer LSTM, hidden=64 → Linear(64, 10) |
| Loss | MSE reconstruction |
| Optimizer | Adam, lr=1e-3, weight_decay=1e-5 |
| LR schedule | ReduceLROnPlateau, patience=5, factor=0.5 |
| Batch size | 64 |
| Max epochs | 50 (early stop patience=10 on val loss) |
| Parameter count | ~200K (estimated) — record exact at training |
| Anomaly score | Mean MSE across channels and time steps |

---

## ARCH-2: GRU Encoder-Decoder (GRU-ED)

**Citation**: Based on Cho et al. (2014) GRU formulation;
encoder-decoder pattern from Sutskever et al. (2014).
Applied to anomaly detection per A9 (TiTAD, MDPI 2025) pattern.

| Parameter | Value |
|---|---|
| Input window | 721 time steps × 10 channels |
| Encoder | 2-layer GRU, hidden=64, dropout=0.1 |
| Latent | Last hidden state, dim=64 |
| Decoder | 2-layer GRU, hidden=64 → Linear(64, 10) |
| Loss | MSE reconstruction |
| Optimizer | Adam, lr=1e-3, weight_decay=1e-5 |
| LR schedule | ReduceLROnPlateau, patience=5, factor=0.5 |
| Batch size | 64 |
| Max epochs | 50 (early stop patience=10 on val loss) |
| Parameter count | ~180K (estimated) — record exact at training |
| Anomaly score | Mean MSE across channels and time steps |

---

## ARCH-3: USAD (CNN/Wavelet-class — UnSupervised Anomaly Detection)

**Citation**: Audibert et al. (2020) "USAD: UnSupervised Anomaly Detection
on Multivariate Time Series", KDD 2020.
https://dl.acm.org/doi/10.1145/3394486.3403392

**Note**: USAD uses two AE networks in an adversarial training scheme.
The input representation uses 1D convolutional layers as the encoder
backbone, placing it in the CNN/wavelet architecture family for this
comparative study. This is stated explicitly in the paper methodology.

| Parameter | Value |
|---|---|
| Input window | 721 time steps × 10 channels (flattened to 7210-dim vector for USAD) |
| Encoder W1/W2 | Linear(7210→512) → Linear(512→128) → Linear(128→64) |
| Decoder W1 | Linear(64→128) → Linear(128→512) → Linear(512→7210) |
| Decoder W2 | Linear(64→128) → Linear(128→512) → Linear(512→7210) |
| Loss | USAD two-phase: phase1=AE1+AE2 MSE; phase2=AE1 adversarial vs AE2 |
| Alpha/Beta schedule | alpha=1/epoch, beta=1-1/epoch (per paper) |
| Optimizer | Adam, lr=1e-3 |
| Batch size | 64 |
| Max epochs | 50 (early stop patience=10 on val loss) |
| Parameter count | ~120K (estimated) — record exact at training |
| Anomaly score | (1-alpha)*AE1_error + alpha*AE12_error (per paper, alpha=0.5 at test) |

---

## ARCH-4: Transformer Autoencoder (TF-AE)

**Citation**: Based on Vaswani et al. (2017) transformer;
anomaly-detection application per A7 (Variable Temporal Transformer,
Knowledge-Based Systems 2024) and A6 (TGB, Scientific Reports 2025).

| Parameter | Value |
|---|---|
| Input window | 721 time steps × 10 channels |
| Input projection | Linear(10 → d_model=32) |
| Positional encoding | Sinusoidal, max_len=721 |
| Encoder | 2 transformer encoder layers, nhead=4, dim_feedforward=128, dropout=0.1 |
| Latent | Mean pooling over time → dim=32 |
| Decoder | Linear(32→128) → Linear(128→721×10) → reshape |
| Loss | MSE reconstruction |
| Optimizer | Adam, lr=1e-4 (lower than RNN models — transformers sensitive to lr) |
| LR schedule | Warmup 5 epochs linear → ReduceLROnPlateau patience=5 |
| Batch size | 64 |
| Max epochs | 50 (early stop patience=10 on val loss) |
| Parameter count | ~250K (estimated) — record exact at training |
| Anomaly score | Mean MSE across channels and time steps |

---

## ML Baselines

### Isolation Forest
- sklearn IsolationForest, n_estimators=200, contamination=0.167 (5/6 classes anomalous)
- Features: flatten (721, 10) → 7210-dim, then PCA to 50 components first
- No training loop; fit on train set, score on test set

### PCA Reconstruction Baseline
- sklearn PCA, n_components=20 (captures ~95% variance on normal class)
- Fit on normal-class train samples only
- Anomaly score: mean squared reconstruction error after inverse_transform
