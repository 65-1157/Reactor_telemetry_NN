"""
architectures.py — Four DL anomaly-detection architectures
============================================================
All implement a common interface:
    forward(x) -> reconstruction
    anomaly_score(x) -> per-sample scalar score

Input shape convention: (batch, T, C) = (B, 721, 10)
"""

import torch
import torch.nn as nn
import math


# ── Shared config ─────────────────────────────────────────────────────────
T_WINDOW = 721
N_CHANNELS = 10


# ══════════════════════════════════════════════════════════════════════════
# ARCH-1: LSTM Autoencoder
# Malhotra et al. (2016) ICML Anomaly Detection Workshop
# ══════════════════════════════════════════════════════════════════════════
class LSTMAutoencoder(nn.Module):
    """
    Two-layer LSTM encoder → latent → two-layer LSTM decoder.
    Input:  (B, T, C)
    Output: (B, T, C)  reconstruction
    """
    def __init__(self, n_channels=N_CHANNELS, hidden=64,
                 n_layers=2, dropout=0.1):
        super().__init__()
        self.hidden   = hidden
        self.n_layers = n_layers
        self.n_channels = n_channels

        self.encoder = nn.LSTM(
            input_size=n_channels, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.decoder = nn.LSTM(
            input_size=n_channels, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.output_proj = nn.Linear(hidden, n_channels)

    def forward(self, x):
        B, T, C = x.shape
        # Encode
        _, (h, c) = self.encoder(x)
        # Decode: feed target shifted by one, teacher-forcing with zeros
        dec_input = torch.zeros(B, T, C, device=x.device, dtype=x.dtype)
        dec_out, _ = self.decoder(dec_input, (h, c))
        return self.output_proj(dec_out)   # (B, T, C)

    def anomaly_score(self, x):
        """Mean squared reconstruction error per sample. Shape: (B,)"""
        with torch.no_grad():
            recon = self.forward(x)
            return ((x - recon) ** 2).mean(dim=(1, 2))


# ══════════════════════════════════════════════════════════════════════════
# ARCH-2: GRU Encoder-Decoder
# Cho et al. (2014) + Sutskever et al. (2014) pattern
# ══════════════════════════════════════════════════════════════════════════
class GRUEncoderDecoder(nn.Module):
    """
    Two-layer GRU encoder → latent → two-layer GRU decoder.
    Input:  (B, T, C)
    Output: (B, T, C)
    """
    def __init__(self, n_channels=N_CHANNELS, hidden=64,
                 n_layers=2, dropout=0.1):
        super().__init__()
        self.hidden = hidden
        self.n_layers = n_layers

        self.encoder = nn.GRU(
            input_size=n_channels, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.decoder = nn.GRU(
            input_size=n_channels, hidden_size=hidden,
            num_layers=n_layers, batch_first=True,
            dropout=dropout if n_layers > 1 else 0.0,
        )
        self.output_proj = nn.Linear(hidden, n_channels)

    def forward(self, x):
        B, T, C = x.shape
        _, h = self.encoder(x)
        dec_input = torch.zeros(B, T, C, device=x.device, dtype=x.dtype)
        dec_out, _ = self.decoder(dec_input, h)
        return self.output_proj(dec_out)

    def anomaly_score(self, x):
        with torch.no_grad():
            recon = self.forward(x)
            return ((x - recon) ** 2).mean(dim=(1, 2))


# ══════════════════════════════════════════════════════════════════════════
# ARCH-3: USAD (UnSupervised Anomaly Detection)
# Audibert et al., KDD 2020
# https://dl.acm.org/doi/10.1145/3394486.3403392
# ══════════════════════════════════════════════════════════════════════════
class USAD(nn.Module):
    """
    Two-AE adversarial scheme per Audibert et al. KDD 2020.
    Input is flattened to (B, T*C) for linear layers.
    Two decoders (W1, W2) trained in two phases per epoch.

    forward() returns (recon_w1, recon_w2) — used in training.
    anomaly_score() uses alpha=0.5 combination at inference.
    """
    def __init__(self, n_channels=N_CHANNELS, t_window=T_WINDOW,
                 latent=64, hidden=512):
        super().__init__()
        in_dim = n_channels * t_window   # 7210

        # Shared encoder
        self.encoder = nn.Sequential(
            nn.Linear(in_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden // 4),
            nn.ReLU(),
            nn.Linear(hidden // 4, latent),
        )
        # Decoder 1 (W1)
        self.decoder1 = nn.Sequential(
            nn.Linear(latent, hidden // 4),
            nn.ReLU(),
            nn.Linear(hidden // 4, hidden),
            nn.ReLU(),
            nn.Linear(hidden, in_dim),
        )
        # Decoder 2 (W2)
        self.decoder2 = nn.Sequential(
            nn.Linear(latent, hidden // 4),
            nn.ReLU(),
            nn.Linear(hidden // 4, hidden),
            nn.ReLU(),
            nn.Linear(hidden, in_dim),
        )
        self.in_dim    = in_dim
        self.t_window  = t_window
        self.n_channels = n_channels

    def forward(self, x):
        """
        Returns (recon_w1, recon_w2) as flat vectors (B, T*C).
        Also returns recon_w12 = decoder2(encoder(decoder1(encoder(x))))
        for the adversarial loss.
        """
        B = x.shape[0]
        x_flat = x.reshape(B, -1)

        z       = self.encoder(x_flat)
        r1      = self.decoder1(z)       # W1 reconstruction
        r2      = self.decoder2(z)       # W2 reconstruction

        # AE12: pass W1 recon through encoder then W2 decoder
        z2      = self.encoder(r1)
        r12     = self.decoder2(z2)      # adversarial term

        return r1, r2, r12

    def anomaly_score(self, x, alpha=0.5):
        """
        Inference score per Audibert et al.:
            score = (1-alpha) * ||x - W1(Z(x))||^2
                  +    alpha  * ||x - W2(Z(W1(Z(x))))||^2
        """
        with torch.no_grad():
            B = x.shape[0]
            x_flat = x.reshape(B, -1)
            r1, _, r12 = self.forward(x)
            err1  = ((x_flat - r1)  ** 2).mean(dim=1)
            err12 = ((x_flat - r12) ** 2).mean(dim=1)
            return (1 - alpha) * err1 + alpha * err12


# ══════════════════════════════════════════════════════════════════════════
# ARCH-4: Transformer Autoencoder (TF-AE)
# Vaswani et al. (2017); anomaly-detection framing per A7 (VTT, KBS 2024)
# ══════════════════════════════════════════════════════════════════════════
class _PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=750, dropout=0.1):
        super().__init__()
        self.dropout = nn.Dropout(dropout)
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0, d_model, 2).float()
                        * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(pos * div)
        pe[:, 1::2] = torch.cos(pos * div)
        self.register_buffer('pe', pe.unsqueeze(0))   # (1, max_len, d_model)

    def forward(self, x):
        return self.dropout(x + self.pe[:, :x.size(1)])


class TransformerAutoencoder(nn.Module):
    """
    Transformer encoder → mean pool → linear decoder.
    Input:  (B, T, C)
    Output: (B, T, C)
    """
    def __init__(self, n_channels=N_CHANNELS, t_window=T_WINDOW,
                 d_model=32, nhead=4, n_layers=2,
                 dim_ff=128, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(n_channels, d_model)
        self.pos_enc    = _PositionalEncoding(d_model, max_len=t_window + 10,
                                               dropout=dropout)
        encoder_layer   = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead,
            dim_feedforward=dim_ff, dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer,
                                                  num_layers=n_layers)
        # Decoder: latent (d_model) → reconstruct full sequence
        self.decoder = nn.Sequential(
            nn.Linear(d_model, dim_ff),
            nn.ReLU(),
            nn.Linear(dim_ff, t_window * n_channels),
        )
        self.t_window   = t_window
        self.n_channels = n_channels

    def forward(self, x):
        B, T, C = x.shape
        z = self.input_proj(x)                # (B, T, d_model)
        z = self.pos_enc(z)
        z = self.transformer(z)               # (B, T, d_model)
        z = z.mean(dim=1)                     # (B, d_model) — mean pool
        out = self.decoder(z)                 # (B, T*C)
        return out.reshape(B, T, C)

    def anomaly_score(self, x):
        with torch.no_grad():
            recon = self.forward(x)
            return ((x - recon) ** 2).mean(dim=(1, 2))


# ── Registry ──────────────────────────────────────────────────────────────
ARCHITECTURE_REGISTRY = {
    "lstm_ae":   LSTMAutoencoder,
    "gru_ed":    GRUEncoderDecoder,
    "usad":      USAD,
    "tf_ae":     TransformerAutoencoder,
}


def build_model(name: str, device: str = "cpu") -> nn.Module:
    """Instantiate a model by name with default spec parameters."""
    cls = ARCHITECTURE_REGISTRY[name]
    model = cls()
    return model.to(device)
