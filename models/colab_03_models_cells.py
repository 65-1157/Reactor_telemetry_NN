# ═══════════════════════════════════════════════════════════════
# 03_models.ipynb — Steps 8-10
# Paste each CELL block below as a new Colab cell.
# Runtime: GPU T4 (Runtime → Change runtime type → T4 GPU)
# ═══════════════════════════════════════════════════════════════


# ── CELL M0: Runtime check ──────────────────────────────────────
import torch
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB")
else:
    print("WARNING: No GPU detected. Switch to T4: Runtime → Change runtime type")


# ── CELL M1: Setup (run every session) ─────────────────────────
!pip install numpy scipy torch scikit-learn matplotlib -q

import subprocess, os
from google.colab import userdata, drive

GITHUB_TOKEN  = userdata.get('GITHUB_TOKEN')
GITHUB_USER   = '65-1157'
REPO_NAME     = 'Reactor_telemetry_NN'
REPO_DIR      = f'/content/{REPO_NAME}'
REPO_URL      = f'https://{GITHUB_TOKEN}@github.com/{GITHUB_USER}/{REPO_NAME}.git'
DRIVE_PROJECT = '/content/drive/MyDrive/Reactor_Telemetry_NN'

drive.mount('/content/drive')

if os.path.exists(REPO_DIR):
    subprocess.run(['git', '-C', REPO_DIR, 'pull'], capture_output=True)
    print('Repo pulled')
else:
    subprocess.run(['git', 'clone', REPO_URL, REPO_DIR], capture_output=True)
    print('Repo cloned')

os.environ['REPO_DIR']      = REPO_DIR
os.environ['DRIVE_PROJECT'] = DRIVE_PROJECT

import sys
sys.path.insert(0, f'{REPO_DIR}/simulator')
sys.path.insert(0, f'{REPO_DIR}/models')
print('Ready.')


# ── CELL M2: Step 8 — Architecture spec confirmation ───────────
# Confirm D9 and D10 are locked before any training starts.
# This cell just prints the spec summary — no computation.

print("=" * 60)
print("STEP 8 — Architecture specifications (LOCKED)")
print("=" * 60)
print()
print("ARCH-1  LSTM Autoencoder      Malhotra et al. 2016")
print("ARCH-2  GRU Encoder-Decoder   Cho et al. 2014 + Sutskever 2014")
print("ARCH-3  USAD                  Audibert et al. KDD 2020  [D9]")
print("ARCH-4  Transformer-AE        Vaswani et al. 2017 + VTT KBS 2024")
print()
print("Baselines: IsolationForest, PCA reconstruction")
print()
print("Reference platform: GPU T4  [D10]")
print("Input shape: (B, 721, 10)   5 seeds per architecture")
print()
print("See models/specs/architecture_specs.md for full details.")


# ── CELL M3: Step 9 — Load dataset, freeze METRICS.md ─────────
import numpy as np, torch, sys, os
sys.path.insert(0, f'{REPO_DIR}/models')
from rbmk_models.trainer import load_splits, make_loaders

DATASET_DIR = f'{DRIVE_PROJECT}/datasets'
CKPT_DIR    = f'{DRIVE_PROJECT}/model_checkpoints'
RESULTS_DIR = f'{DRIVE_PROJECT}/results'

for d in [CKPT_DIR, RESULTS_DIR]:
    os.makedirs(d, exist_ok=True)

print("Loading dataset splits...")
splits  = load_splits(DATASET_DIR, device='cpu')
loaders = make_loaders(splits, batch_size=64)
print()
print("METRICS.md frozen — point-wise protocol, 95th-pct threshold,")
print("5 seeds per architecture, AUROC+AUPRC primary, T4 GPU platform.")
print()
print(f"Train batches per epoch: {len(loaders['train'])}")
print(f"Val   batches per epoch: {len(loaders['val'])}")


# ── CELL M4: Step 10 — Train all architectures (5 seeds each) ──
# Expected total time on T4: ~25-40 minutes for all 4 architectures.
import torch, json, os, time
from rbmk_models.architectures import build_model, ARCHITECTURE_REGISTRY
from rbmk_models.trainer       import train_model, save_model

SEEDS    = [42, 7, 13, 99, 2024]
ARCH_LRS = {
    "lstm_ae": 1e-3,
    "gru_ed":  1e-3,
    "usad":    1e-3,
    "tf_ae":   1e-4,   # lower LR for transformer
}
ARCH_WARMUP = {
    "lstm_ae": 0,
    "gru_ed":  0,
    "usad":    0,
    "tf_ae":   5,      # 5-epoch linear warmup
}

all_train_logs = {}

for arch_name in ["lstm_ae", "gru_ed", "usad", "tf_ae"]:
    print(f"\n{'='*60}")
    print(f"Training {arch_name.upper()}  ({len(SEEDS)} seeds)")
    print(f"{'='*60}")

    seed_results = []
    for seed in SEEDS:
        print(f"\n  Seed {seed}:")
        model = build_model(arch_name, device=device)

        best_val, logs = train_model(
            model=model,
            loaders=loaders,
            arch_name=arch_name,
            device=device,
            n_epochs=50,
            lr=ARCH_LRS[arch_name],
            lr_warmup=ARCH_WARMUP[arch_name],
            results_dir=RESULTS_DIR,
            seed=seed,
        )
        save_model(model, f"{arch_name}_seed{seed}", CKPT_DIR)
        seed_results.append({"seed": seed, "best_val": best_val})

    all_train_logs[arch_name] = seed_results
    print(f"\n  {arch_name} seeds done. "
          f"Val losses: {[f'{r[\"best_val\"]:.5f}' for r in seed_results]}")

# Save aggregate training summary
with open(f'{RESULTS_DIR}/training_summary.json', 'w') as f:
    json.dump(all_train_logs, f, indent=2)
print("\nAll architectures trained. Summary saved.")


# ── CELL M5: Step 10 — Evaluate all architectures ──────────────
import json
from rbmk_models.architectures import build_model
from rbmk_models.trainer       import load_model
from rbmk_models.evaluator     import (evaluate_architecture,
                                        evaluate_baselines,
                                        print_summary_table)

all_results = {}

for arch_name in ["lstm_ae", "gru_ed", "usad", "tf_ae"]:
    print(f"\nEvaluating {arch_name} (best seed by val loss)...")

    # Find best seed
    with open(f'{RESULTS_DIR}/training_summary.json') as f:
        summary = json.load(f)

    best_seed = min(summary[arch_name], key=lambda x: x['best_val'])['seed']
    print(f"  Best seed: {best_seed}")

    model = build_model(arch_name, device=device)
    load_model(model, f"{arch_name}_seed{best_seed}", CKPT_DIR, device)

    log_path = f"{RESULTS_DIR}/training_log_{arch_name}.json"
    result   = evaluate_architecture(
        model, arch_name, splits, device,
        training_log_path=log_path,
        results_dir=RESULTS_DIR,
        seed=best_seed,
    )
    all_results[arch_name] = result

# Baselines
print("\nEvaluating baselines...")
baseline_results = evaluate_baselines(splits, RESULTS_DIR)
all_results.update(baseline_results)

# Summary table
print_summary_table(all_results)

# Save combined results
with open(f'{RESULTS_DIR}/all_results.json', 'w') as f:
    json.dump(all_results, f, indent=2)
print(f"\nAll results saved: {RESULTS_DIR}/all_results.json")


# ── CELL M6: Visualise results ──────────────────────────────────
import matplotlib.pyplot as plt
import json, numpy as np

with open(f'{RESULTS_DIR}/all_results.json') as f:
    all_results = json.load(f)

arch_names = ["lstm_ae", "gru_ed", "usad", "tf_ae"]
labels     = ["LSTM-AE", "GRU-ED", "USAD", "TF-AE"]
baselines  = ["isolation_forest", "pca"]
bl_labels  = ["IsolationForest", "PCA"]

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Step 10 — Engineering-Axis Comparison", fontsize=12)

# AUROC / AUPRC
x = np.arange(len(arch_names))
w = 0.35
auroc = [all_results[a]['auroc'] for a in arch_names]
auprc = [all_results[a]['auprc'] for a in arch_names]
axes[0].bar(x - w/2, auroc, w, label='AUROC', color='steelblue')
axes[0].bar(x + w/2, auprc, w, label='AUPRC', color='tomato')
for bl, bll in zip(baselines, bl_labels):
    if bl in all_results:
        axes[0].axhline(all_results[bl]['auroc'], ls='--', lw=1,
                        label=f'{bll} AUROC')
axes[0].set_xticks(x); axes[0].set_xticklabels(labels)
axes[0].set_ylim(0, 1); axes[0].set_title('Detection Performance')
axes[0].legend(fontsize=8); axes[0].grid(alpha=0.3, axis='y')

# Parameter count
params = [all_results[a]['param_count'] for a in arch_names]
axes[1].bar(labels, params, color='mediumseagreen')
axes[1].set_title('Parameter Count')
axes[1].set_ylabel('Trainable parameters')
axes[1].grid(alpha=0.3, axis='y')
for i, v in enumerate(params):
    axes[1].text(i, v + max(params)*0.01, f'{v/1e3:.0f}K',
                 ha='center', fontsize=9)

# Inference latency
latency = [all_results[a].get('latency_ms_median', 0) for a in arch_names]
axes[2].bar(labels, latency, color='darkorange')
axes[2].set_title('Inference Latency (ms/sample)')
axes[2].set_ylabel('ms'); axes[2].grid(alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(f'{DRIVE_PROJECT}/figures/step10_engineering_axis.png',
            dpi=150, bbox_inches='tight')
plt.show()
print("Figure saved to Drive.")


# ── CELL M7: Commit model code to GitHub ───────────────────────
# Note: checkpoints and results stay on Drive (too large for git).
# Only the Python modules and spec docs go to GitHub.
import subprocess

def git(args):
    r = subprocess.run(['git']+args, cwd=REPO_DIR,
                       capture_output=True, text=True)
    out = (r.stdout+r.stderr).strip()
    if out: print(out)
    return r.returncode

git(['config', 'user.email', 'colab@reactor-telemetry-nn'])
git(['config', 'user.name',  'Colab Session'])
git(['remote', 'set-url', 'origin', REPO_URL])

git(['add',
     'models/rbmk_models/__init__.py',
     'models/rbmk_models/architectures.py',
     'models/rbmk_models/trainer.py',
     'models/rbmk_models/evaluator.py',
     'models/specs/architecture_specs.md',
     'models/METRICS.md',
     'models/.gitkeep',
])

status = subprocess.run(['git','status','--short'], cwd=REPO_DIR,
                        capture_output=True, text=True).stdout.strip()
if not status:
    print('Nothing new to commit')
else:
    git(['commit', '-m',
         'Steps 8-10: architecture specs, METRICS.md, '
         'LSTM-AE/GRU-ED/USAD/TF-AE implementations + trainer + evaluator; '
         'results on Drive'])
    git(['push', 'origin', 'main'])
    log = subprocess.run(['git','log','--oneline','-4'],
                         cwd=REPO_DIR, capture_output=True, text=True).stdout
    print(f'Latest commits:\n{log}')
