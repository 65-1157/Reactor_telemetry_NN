"""
kinetics.py — ODE system (corrected normalisation)
====================================================
State vector (10 elements):
  [0]     P       : normalised power (P/P_nominal)
  [1..6]  C_i     : DN precursor concentrations (normalised, ~O(1))
  [7]     I_raw   : I-135 concentration in raw units (I_EQ_RAW at P=1 eq.)
  [8]     Xe_raw  : Xe-135 concentration in raw units (XE_EQ_RAW at P=1 eq.)
  [9]     T_fuel  : fuel centreline temperature (K)

Output dict normalises I and Xe: I_norm = I_raw/I_EQ_RAW, Xe_norm = Xe_raw/XE_EQ_RAW.
xenon_reactivity() in feedback.py takes Xe_norm (= Xe_raw/XE_EQ_RAW).
"""

import numpy as np
from scipy.integrate import solve_ivp

from .params import (
    BETA_GROUP, LAMBDA_GROUP, BETA_TOTAL, LAMBDA_PROMPT,
    LAMBDA_I, LAMBDA_XE, GAMMA_I, SIGMA_XE, PHI_NOMINAL,
    TAU_FUEL, T_FUEL_NOMINAL, T_FUEL_INLET,
    ODE_METHOD, ODE_ATOL, ODE_RTOL, PCM,
    I_EQ_RAW, XE_EQ_RAW, PROD_I_RATE, SIGMA_XE_PHI,
)
from .feedback import total_reactivity



def equilibrium_rod_reactivity(void_frac: float = 0.30, Xe_norm: float = 1.0) -> float:
    """Rod reactivity (dk/k) needed for criticality at P=1 given void and Xe."""
    from .feedback import void_reactivity, doppler_reactivity, xenon_reactivity
    rv  = void_reactivity(void_frac)
    rd  = doppler_reactivity(T_FUEL_NOMINAL)
    rxe = xenon_reactivity(Xe_norm, PHI_NOMINAL)
    return -(rv + rd + rxe)


def _steady_state(void_frac: float = 0.30) -> np.ndarray:
    """Equilibrium state vector at P=1 and given void fraction."""
    P    = 1.0
    C_eq = (BETA_GROUP / LAMBDA_PROMPT) * P / LAMBDA_GROUP
    # Raw equilibrium concentrations (true zeros of dI/dt and dXe/dt at P=1)
    I_eq  = I_EQ_RAW   # raw units
    Xe_eq = XE_EQ_RAW  # raw units

    y0 = np.empty(10)
    y0[0]   = P
    y0[1:7] = C_eq
    y0[7]   = I_eq
    y0[8]   = Xe_eq
    y0[9]   = T_FUEL_NOMINAL
    return y0


def _odefun(t, y, rho_rod_fn, void_frac_fn):
    P      = max(y[0], 0.0)
    C      = y[1:7]
    I_raw  = max(y[7], 0.0)
    Xe_raw = max(y[8], 0.0)
    T_fuel = y[9]

    # Normalise Xe for the reactivity feedback
    Xe_norm = Xe_raw / XE_EQ_RAW

    rho_rod   = rho_rod_fn(t)
    void_frac = float(np.clip(void_frac_fn(t), 0.0, 1.0))

    rho_tot, _, _, _, _ = total_reactivity(
        rho_rod, void_frac, T_fuel, Xe_norm, phi=PHI_NOMINAL * P
    )

    # Point kinetics
    dP  = ((rho_tot - BETA_TOTAL) / LAMBDA_PROMPT) * P + np.dot(LAMBDA_GROUP, C)
    dC  = (BETA_GROUP / LAMBDA_PROMPT) * P - LAMBDA_GROUP * C

    # Xe/I balance in raw units (P-normalised production, correct units)
    dI   = PROD_I_RATE * P - LAMBDA_I * I_raw
    dXe  = LAMBDA_I * I_raw - (LAMBDA_XE + SIGMA_XE_PHI * P) * Xe_raw

    # Fuel temperature: first-order lag
    T_target = T_FUEL_NOMINAL * P + T_FUEL_INLET * (1.0 - P)
    dT = (T_target - T_fuel) / TAU_FUEL

    dydt = np.empty(10)
    dydt[0]   = dP
    dydt[1:7] = dC
    dydt[7]   = dI
    dydt[8]   = dXe
    dydt[9]   = dT
    return dydt


def run(t_span, t_eval, rho_rod_fn, void_frac_fn, void_frac_init=0.30):
    y0     = _steady_state(void_frac_init)
    t_eval = np.asarray(t_eval)
    t_eval = t_eval[(t_eval >= t_span[0]) & (t_eval <= t_span[1])]

    sol = solve_ivp(
        fun=lambda t, y: _odefun(t, y, rho_rod_fn, void_frac_fn),
        t_span=t_span, y0=y0,
        method=ODE_METHOD, t_eval=t_eval,
        atol=ODE_ATOL, rtol=ODE_RTOL,
    )
    if not sol.success:
        raise RuntimeError(f"ODE solver failed: {sol.message}")

    P      = np.clip(sol.y[0], 0.0, None)
    I_raw  = sol.y[7]
    Xe_raw = sol.y[8]
    Tf     = sol.y[9]
    t      = sol.t

    # Normalise Xe/I for output
    I_norm  = I_raw  / I_EQ_RAW
    Xe_norm = Xe_raw / XE_EQ_RAW

    vf  = np.array([float(np.clip(void_frac_fn(ti), 0, 1)) for ti in t])
    rr  = np.array([rho_rod_fn(ti) for ti in t])
    rv, rd, rxe, rtot = (np.empty(len(t)) for _ in range(4))

    for i in range(len(t)):
        rtot[i], _, rv[i], rd[i], rxe[i] = total_reactivity(
            rr[i], vf[i], Tf[i], Xe_norm[i], phi=PHI_NOMINAL * P[i]
        )

    return {
        "t":               t,
        "P":               P,
        "C":               sol.y[1:7],
        "I":               I_norm,
        "Xe":              Xe_norm,
        "T_fuel":          Tf,
        "void_fraction":   vf,
        "rho_rod_pcm":     rr   / PCM,
        "rho_void_pcm":    rv   / PCM,
        "rho_doppler_pcm": rd   / PCM,
        "rho_xenon_pcm":   rxe  / PCM,
        "rho_total_pcm":   rtot / PCM,
    }
