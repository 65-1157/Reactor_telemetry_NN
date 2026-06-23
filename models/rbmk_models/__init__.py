"""
rbmk_models — DL architecture implementations for comparative study
=====================================================================
Four architectures + two baselines, per architecture_specs.md.

Modules
-------
architectures   : LSTM-AE, GRU-ED, USAD, Transformer-AE
baselines       : IsolationForest, PCA reconstruction
trainer         : shared training loop, early stopping, logging
evaluator       : AUROC, AUPRC, latency, param count, FLOPs
"""
