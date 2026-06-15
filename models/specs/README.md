# /models/specs/

One Markdown file per architecture:

- `lstm_ae.md`
- `gru_encoder_decoder.md`
- `cnn_wavelet.md` (variant still to be fixed — see open items)
- `transformer.md`

Each must specify: parameter count, input window length, loss function,
optimizer and learning-rate strategy, and the reference platform used for
latency/memory measurement (must match `/models/METRICS.md`).
