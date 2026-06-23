"""
trainer.py — Shared training loop
===================================
Handles all four architectures via duck-typing:
  - Standard AE (LSTM-AE, GRU-ED, TF-AE): single forward + MSE loss
  - USAD: two-phase training per Audibert et al. KDD 2020

Logs per-epoch train/val loss, wall-clock time, and GPU memory.
All logs written to results/training_log.json for the paper tables.
"""

import time, json, os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


# ── Dataset loader ────────────────────────────────────────────────────────

def load_splits(dataset_dir: str, device: str = "cpu"):
    """
    Load train/val/test splits from Drive .npz files.
    Returns dict of {split: (X_tensor, y_tensor, gt_channels)}.
    """
    import numpy as np
    splits = {}
    for split in ("train", "val", "test"):
        data = np.load(f"{dataset_dir}/{split}.npz", allow_pickle=True)
        X = torch.tensor(data["X"], dtype=torch.float32)
        y = torch.tensor(data["y"], dtype=torch.long)
        gt = data["gt_channel"]
        splits[split] = (X, y, gt)
        print(f"  {split:6s}: X={tuple(X.shape)}  y={tuple(y.shape)}")
    return splits


def make_loaders(splits, batch_size=64):
    """Return DataLoaders for train and val (X only — unsupervised)."""
    loaders = {}
    for split in ("train", "val"):
        X, _, _ = splits[split]
        ds = TensorDataset(X)
        shuffle = (split == "train")
        loaders[split] = DataLoader(ds, batch_size=batch_size,
                                     shuffle=shuffle, pin_memory=True,
                                     num_workers=0)
    return loaders


# ── USAD loss ─────────────────────────────────────────────────────────────

def usad_loss(model, x_flat, epoch, n_epochs):
    """
    Two-phase USAD loss per Audibert et al. KDD 2020.
    Phase 1: train both AEs to reconstruct input
    Phase 2: train AE1 to fool AE2, train AE2 to detect AE1 output
    """
    n = epoch / n_epochs
    r1, r2, r12 = model(x_flat.reshape(x_flat.shape[0], -1).unsqueeze(1)
                         .expand(-1, 1, -1).squeeze(1))

    # Re-call forward properly (model takes (B, T, C))
    r1, r2, r12 = model(x_flat)

    x_f = x_flat.reshape(x_flat.shape[0], -1)
    loss1 = (1/n) * ((x_f - r1)**2).mean() + (1 - 1/n) * ((x_f - r12)**2).mean()
    loss2 = (1/n) * ((x_f - r2)**2).mean() - (1 - 1/n) * ((x_f - r12)**2).mean()
    return loss1, loss2


# ── Standard AE loss ──────────────────────────────────────────────────────

def ae_loss(model, x):
    recon = model(x)
    return ((x - recon) ** 2).mean()


# ── Early stopping ────────────────────────────────────────────────────────

class EarlyStopping:
    def __init__(self, patience=10, min_delta=1e-6):
        self.patience   = patience
        self.min_delta  = min_delta
        self.best_loss  = float("inf")
        self.counter    = 0
        self.best_state = None

    def step(self, val_loss, model):
        if val_loss < self.best_loss - self.min_delta:
            self.best_loss  = val_loss
            self.counter    = 0
            self.best_state = {k: v.cpu().clone()
                               for k, v in model.state_dict().items()}
        else:
            self.counter += 1
        return self.counter >= self.patience

    def restore(self, model):
        if self.best_state:
            model.load_state_dict(self.best_state)


# ── Main training function ────────────────────────────────────────────────

def train_model(
    model,
    loaders,
    arch_name: str,
    device: str,
    n_epochs: int = 50,
    lr: float = 1e-3,
    lr_warmup: int = 0,
    results_dir: str = ".",
    seed: int = 42,
):
    """
    Train model for up to n_epochs with early stopping.
    Logs training metrics to results_dir/training_log_{arch_name}.json.

    Returns: best_val_loss, epoch_logs
    """
    torch.manual_seed(seed)
    model = model.to(device)
    is_usad = arch_name == "usad"

    if is_usad:
        # Two optimizers for USAD
        opt1 = torch.optim.Adam(
            list(model.encoder.parameters()) +
            list(model.decoder1.parameters()), lr=lr)
        opt2 = torch.optim.Adam(
            list(model.encoder.parameters()) +
            list(model.decoder2.parameters()), lr=lr)
        sched1 = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt1, patience=5, factor=0.5)
        sched2 = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt2, patience=5, factor=0.5)
    else:
        opt   = torch.optim.Adam(model.parameters(), lr=lr,
                                  weight_decay=1e-5)
        if lr_warmup > 0:
            # Linear warmup then ReduceLROnPlateau
            warmup_sched = torch.optim.lr_scheduler.LinearLR(
                opt, start_factor=0.1, end_factor=1.0, total_iters=lr_warmup)
        else:
            warmup_sched = None
        plateau_sched = torch.optim.lr_scheduler.ReduceLROnPlateau(
            opt, patience=5, factor=0.5)

    stopper  = EarlyStopping(patience=10)
    logs     = []
    t_train_start = time.time()

    for epoch in range(1, n_epochs + 1):
        # ── Training ──────────────────────────────────────────────────────
        model.train()
        train_losses = []
        t_ep = time.time()

        for (x_batch,) in loaders["train"]:
            x_batch = x_batch.to(device)

            if is_usad:
                n  = epoch / n_epochs
                x_f = x_batch
                r1, r2, r12 = model(x_f)
                x_flat = x_f.reshape(x_f.shape[0], -1)
                r1f = r1; r2f = r2; r12f = r12

                l1 = ((1/n) * ((x_flat - r1f)**2).mean()
                      + (1 - 1/n) * ((x_flat - r12f)**2).mean())
                l2 = ((1/n) * ((x_flat - r2f)**2).mean()
                      - (1 - 1/n) * ((x_flat - r12f)**2).mean())

                opt1.zero_grad(); l1.backward(retain_graph=True); opt1.step()
                opt2.zero_grad(); l2.backward(); opt2.step()
                train_losses.append((l1 + l2).item())
            else:
                loss = ae_loss(model, x_batch)
                opt.zero_grad(); loss.backward(); opt.step()
                train_losses.append(loss.item())

        # ── Validation ────────────────────────────────────────────────────
        model.eval()
        val_losses = []
        with torch.no_grad():
            for (x_batch,) in loaders["val"]:
                x_batch = x_batch.to(device)
                if is_usad:
                    r1, r2, r12 = model(x_batch)
                    xf = x_batch.reshape(x_batch.shape[0], -1)
                    v  = (0.5 * ((xf-r1)**2).mean()
                          + 0.5 * ((xf-r12)**2).mean())
                    val_losses.append(v.item())
                else:
                    val_losses.append(ae_loss(model, x_batch).item())

        train_loss = sum(train_losses) / len(train_losses)
        val_loss   = sum(val_losses)   / len(val_losses)
        ep_time    = time.time() - t_ep

        # GPU memory
        if device != "cpu" and torch.cuda.is_available():
            mem_mb = torch.cuda.max_memory_allocated(device) / 1e6
        else:
            mem_mb = 0.0

        ep_log = {
            "epoch": epoch, "train_loss": train_loss,
            "val_loss": val_loss, "epoch_time_s": ep_time,
            "gpu_mem_mb": mem_mb,
        }
        logs.append(ep_log)

        if epoch % 5 == 0 or epoch == 1:
            print(f"  [{arch_name}] ep={epoch:3d}  "
                  f"train={train_loss:.5f}  val={val_loss:.5f}  "
                  f"t={ep_time:.1f}s  mem={mem_mb:.0f}MB")

        # LR schedulers
        if is_usad:
            sched1.step(val_loss)
            sched2.step(val_loss)
        else:
            if warmup_sched and epoch <= lr_warmup:
                warmup_sched.step()
            else:
                plateau_sched.step(val_loss)

        # Early stopping
        if stopper.step(val_loss, model):
            print(f"  [{arch_name}] Early stop at epoch {epoch} "
                  f"(best val={stopper.best_loss:.5f})")
            break

    stopper.restore(model)
    total_time = time.time() - t_train_start

    # Save log
    os.makedirs(results_dir, exist_ok=True)
    log_path = f"{results_dir}/training_log_{arch_name}.json"
    with open(log_path, "w") as f:
        json.dump({"arch": arch_name, "seed": seed,
                   "total_time_s": total_time,
                   "best_val_loss": stopper.best_loss,
                   "epochs": logs}, f, indent=2)
    print(f"  [{arch_name}] Training complete. "
          f"Total={total_time:.1f}s  best_val={stopper.best_loss:.5f}")
    print(f"  Log saved: {log_path}")

    return stopper.best_loss, logs


# ── Model save/load ───────────────────────────────────────────────────────

def save_model(model, arch_name: str, ckpt_dir: str):
    os.makedirs(ckpt_dir, exist_ok=True)
    path = f"{ckpt_dir}/{arch_name}_best.pt"
    torch.save(model.state_dict(), path)
    print(f"  Saved: {path}")
    return path


def load_model(model, arch_name: str, ckpt_dir: str, device: str):
    path = f"{ckpt_dir}/{arch_name}_best.pt"
    model.load_state_dict(torch.load(path, map_location=device))
    model.eval()
    return model
