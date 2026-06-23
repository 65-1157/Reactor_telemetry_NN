"""
feedback.py — Reactivity feedback terms
========================================
Each function returns a reactivity contribution in dk/k (dimensionless).
Keeping these separate from the ODE makes unit-testing trivial and makes
the interpretability attribution (which channel drives the anomaly) direct.
"""

from .params import (
    ALPHA_VOID, ALPHA_DOPPLER, SIGMA_XE, PHI_NOMINAL,
    T_FUEL_NOMINAL, PCM,
)


def void_reactivity(void_fraction: float) -> float:
    """
    rho_void = alpha_void * void_pct
    void_fraction : float in [0, 1]  (0 = fully liquid, 1 = fully steam)
    Returns dk/k.
    """
    void_pct = void_fraction * 100.0          # convert to % for coefficient
    return ALPHA_VOID * void_pct


def doppler_reactivity(T_fuel: float) -> float:
    """
    rho_doppler = alpha_doppler * (T_fuel - T_nominal)
    T_fuel : fuel centreline temperature (K)
    Returns dk/k.
    """
    return ALPHA_DOPPLER * (T_fuel - T_FUEL_NOMINAL)


def xenon_reactivity(Xe: float, phi: float = PHI_NOMINAL) -> float:
    """
    rho_xenon = -sigma_Xe * Xe * phi / (Sigma_f_phi_nominal)
    Expressed as a normalised reactivity:
      rho_xenon(t) proportional to -Xe(t) * phi(t)
    We carry Xe in normalised units (Xe_norm = Xe / Xe_eq at nominal power)
    so the equilibrium xenon gives a known reactivity worth.

    At equilibrium, Xe_eq * sigma_Xe * phi_nominal ~ xenon_worth_at_eq.
    We set that worth = -2800 pcm, representative of a large thermal reactor
    at full power (standard reactor-physics estimate; see DESIGN_NOTE.md).

    rho_xenon = -2800 pcm * Xe_norm * (phi / phi_nominal)
    Returns dk/k.
    """
    XE_WORTH_EQ = -2800.0 * PCM    # equilibrium xenon worth at nominal power
    phi_norm    = phi / PHI_NOMINAL
    return XE_WORTH_EQ * Xe * phi_norm


def total_reactivity(
    rho_rod:  float,
    void_frac: float,
    T_fuel:   float,
    Xe_norm:  float,
    phi:      float = PHI_NOMINAL,
) -> tuple[float, float, float, float, float]:
    """
    Decompose total reactivity into four terms.
    Returns (rho_total, rho_rod, rho_void, rho_doppler, rho_xenon)  in dk/k.
    All four components are returned so the dataset can log each one
    separately — this is what enables ground-truth anomaly attribution.
    """
    rv   = void_reactivity(void_frac)
    rd   = doppler_reactivity(T_fuel)
    rxe  = xenon_reactivity(Xe_norm, phi)
    rtot = rho_rod + rv + rd + rxe
    return rtot, rho_rod, rv, rd, rxe
