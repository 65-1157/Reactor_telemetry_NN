"""
params.py — Frozen simulator parameters
========================================
All values locked in DESIGN_DECISIONS.md (D1–D10).
Do NOT edit without logging a justification in simulator/DESIGN_NOTE.md
Section 8 and updating DESIGN_DECISIONS.md.

Sources
-------
B4  : arXiv:1307.7670  (Xe/I constants — decay constants and yields)
D1-A: Lamarsh/Keepin thermal-U-235 six-group table
D3-B: Lambda = 1e-3 s  (graphite-moderator literature)
D4-B: alpha_void = +10 pcm/% void  (mid-range, Chernobyl firewall)
D5-A: alpha_doppler = -1.5 pcm/K
D6-B: tau_fuel = 15 s
EPJ-N 2023: DOI 10.1051/epjn/2023017
sigma_Xe note: B4 reports 2.50e-19 cm^2 (fast/epithermal TRIGA spectrum).
  For the thermal RBMK-class model, the standard thermal-spectrum value
  2.60e-18 cm^2 (~2.6e6 barns) is used. Logged as a scope note; this is
  not a Chernobyl-calibration adjustment.
"""

import numpy as np

# ---------------------------------------------------------------------------
# Unit conversion
# ---------------------------------------------------------------------------
PCM = 1e-5          # 1 pcm = 1e-5 dk/k

# ---------------------------------------------------------------------------
# Six-group delayed-neutron data  [D1-A: Lamarsh/Keepin thermal U-235]
# ---------------------------------------------------------------------------
BETA_GROUP = np.array([
    0.000247,   # group 1
    0.0013845,  # group 2
    0.001222,   # group 3
    0.0026455,  # group 4
    0.0008320,  # group 5
    0.0001690,  # group 6
], dtype=np.float64)

LAMBDA_GROUP = np.array([
    0.0124,     # group 1  (s^-1)
    0.0305,     # group 2
    0.111,      # group 3
    0.301,      # group 4
    1.14,       # group 5
    3.01,       # group 6
], dtype=np.float64)

BETA_TOTAL = float(BETA_GROUP.sum())
N_GROUPS   = len(BETA_GROUP)           # 6

# ---------------------------------------------------------------------------
# Prompt neutron generation time  [D3-B]
# ---------------------------------------------------------------------------
LAMBDA_PROMPT = 1e-3    # s

# ---------------------------------------------------------------------------
# Xe-135 / I-135 constants  [B4: arXiv:1307.7670, Table 1 — decay constants]
# Two-step chain adopted (D2-A)
# ---------------------------------------------------------------------------
LAMBDA_I  = 2.90e-5     # I-135 decay constant  (s^-1)
LAMBDA_XE = 2.10e-5     # Xe-135 decay constant (s^-1)
GAMMA_I   = 3.03e-2     # I-135 cumulative fission yield per fission
SIGMA_XE  = 2.60e-18    # Xe-135 thermal absorption cross-section (cm^2)
                         # Standard thermal-spectrum value (~2.6e6 barns)

PHI_NOMINAL = 1.0e13    # n cm^-2 s^-1 — nominal average thermal flux

# ---------------------------------------------------------------------------
# Reactivity feedback coefficients
# ---------------------------------------------------------------------------
ALPHA_VOID    = +10.0 * PCM   # dk/k per % void  [D4-B]
ALPHA_DOPPLER = -1.5  * PCM   # dk/k per K        [D5-A]

# ---------------------------------------------------------------------------
# Fuel temperature model  [D6-B]
# ---------------------------------------------------------------------------
TAU_FUEL       = 15.0          # s
T_FUEL_NOMINAL = 920.0         # K — nominal fuel centreline temp at P=1
T_FUEL_INLET   = 270.0 + 273.15  # K — coolant inlet (~270°C)

# ---------------------------------------------------------------------------
# Equilibrium xenon worth (at P=1, phi=phi_nominal)
# Normalisation constant for xenon_reactivity() in feedback.py
# ~-2800 pcm is representative for a large thermal reactor at full power.
# ---------------------------------------------------------------------------
XE_WORTH_EQ_PCM = -2800.0   # pcm

# ---------------------------------------------------------------------------
# ODE solver  [D7-A]
# ---------------------------------------------------------------------------
ODE_METHOD = "LSODA"
ODE_ATOL   = 1e-8
ODE_RTOL   = 1e-6

# ---------------------------------------------------------------------------
# Output channels  [D8]
# ---------------------------------------------------------------------------
CHANNELS = {
    "CH01": ("reactor_power_norm",       "dimensionless", "all"),
    "CH02": ("total_reactivity_pcm",     "pcm",           "all"),
    "CH03": ("void_fraction",            "fraction",      "void"),
    "CH04": ("void_reactivity_pcm",      "pcm",           "void"),
    "CH05": ("xenon_reactivity_pcm",     "pcm",           "xenon"),
    "CH06": ("xenon_concentration_norm", "dimensionless", "xenon"),
    "CH07": ("iodine_concentration_norm","dimensionless", "xenon"),
    "CH08": ("fuel_temperature_K",       "K",             "doppler"),
    "CH09": ("rod_reactivity_pcm",       "pcm",           "rod"),
    "CH10": ("doppler_reactivity_pcm",   "pcm",           "doppler"),
}
CHANNEL_NAMES = list(CHANNELS.keys())
N_CHANNELS    = len(CHANNELS)

# ---------------------------------------------------------------------------
# Xe/I equilibrium normalisation constants
# These are the RAW equilibrium values at P=1, phi=phi_nominal.
# State variables I and Xe in the ODE are stored in these units;
# output is normalised by these values (= 1.0 at P=1 full-power equilibrium).
# ---------------------------------------------------------------------------
import numpy as _np
I_EQ_RAW  = GAMMA_I / LAMBDA_I                          # = 1.0448e+03
XE_EQ_RAW = (LAMBDA_I * (GAMMA_I / LAMBDA_I)            # = 6.4468e+02
             / (LAMBDA_XE + SIGMA_XE * PHI_NOMINAL))

# Xe/I ODE production/burnout rate constants (normalised to phi_nominal)
# These ensure dI/dt=0, dXe/dt=0 exactly at P=1, Xe=XE_EQ_RAW, I=I_EQ_RAW
PROD_I_RATE  = LAMBDA_I * I_EQ_RAW       # I-135 production rate at P=1 (s^-1)
SIGMA_XE_PHI = SIGMA_XE * PHI_NOMINAL    # Xe-135 burnout rate at phi_nominal (s^-1)
