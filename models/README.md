# /models/

- `specs/` — one frozen spec sheet per architecture (LSTM Autoencoder, GRU
  Encoder-Decoder, CNN/Wavelet-based, Transformer-based): parameter count,
  input window, loss function, optimizer/LR strategy, and the fixed
  reference platform for latency/memory measurement. The CNN/Wavelet variant
  must be a single, named, citable published design (open item).
- `METRICS.md` — frozen before any training run. Primary metrics (AUROC,
  AUPRC), secondary metrics (latency, FLOPs, memory — on the platform fixed
  in `specs/`), interpretability metrics (Top-1/Top-3 attribution accuracy),
  evaluation protocol, and repetition/seed policy.
- Shared training pipeline code, plus simple baselines (Isolation Forest,
  PCA).
- `results/` — engineering-axis evaluation outputs.
