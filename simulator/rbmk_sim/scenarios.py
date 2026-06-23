"""
scenarios.py — Scenario builders
==================================
All builders return (rho_rod_fn, void_frac_fn, label, gt_channel).
rho_rod_fn returns the TOTAL rod reactivity (baseline + deviation).
The baseline rod reactivity compensates void + Doppler + xenon at P=1.
AZ-5 / positive-scram transient EXPLICITLY excluded (LIMITATIONS.md §4, V04).
"""

import numpy as np
from .params import PCM, BETA_TOTAL


def _get_baseline():
    """Return equilibrium rod reactivity at nominal conditions."""
    from .kinetics import equilibrium_rod_reactivity
    return equilibrium_rod_reactivity(void_frac=0.30, Xe_norm=1.0)


def _piecewise(breakpoints):
    ts = np.array([b[0] for b in breakpoints])
    vs = np.array([b[1] for b in breakpoints])
    return lambda t: float(np.interp(t, ts, vs))


def normal_operation(duration=7200.0, rng=None, **kw):
    """Normal full-power operation with minor sinusoidal rod dither."""
    if rng is None: rng = np.random.default_rng()
    baseline = _get_baseline()
    ROD_DITHER = 5.0 * PCM

    def rho_rod(t):
        return baseline + ROD_DITHER * np.sin(2 * np.pi * t / 1200.0) * 0.5

    return rho_rod, lambda t: 0.30, "normal", None


def anomaly_void_spike(duration=7200.0, t_onset=1800.0,
                       delta_void=0.15, rng=None, **kw):
    """Void fraction rises at t_onset. Ground truth: CH03/CH04."""
    baseline = _get_baseline()
    NOMINAL_VOID = 0.30
    void_fn = _piecewise([
        (0.0,            NOMINAL_VOID),
        (t_onset,        NOMINAL_VOID),
        (t_onset + 60.0, NOMINAL_VOID + delta_void),
        (duration,       NOMINAL_VOID + delta_void),
    ])
    return lambda t: baseline, void_fn, "void_spike", "CH03"


def anomaly_xenon_pit(duration=36000.0, t_onset=1800.0,
                      power_step=0.5, rng=None, **kw):
    """Power step down triggers iodine-pit xenon transient. GT: CH05/CH06/CH07."""
    baseline = _get_baseline()

    def rho_rod(t):
        if t < t_onset:
            return baseline
        ramp = min((t - t_onset) / 3600.0, 1.0)
        # Partial rod withdrawal to compensate xenon build-up
        return baseline - 50.0 * PCM * ramp * power_step

    return rho_rod, lambda t: 0.30, "xenon_pit", "CH05"


def anomaly_rod_withdrawal(duration=7200.0, t_onset=1800.0,
                            withdrawal_rate=2.0, max_withdrawal=150.0,
                            rng=None, **kw):
    """Gradual additional rod withdrawal above baseline. GT: CH09."""
    baseline = _get_baseline()

    def rho_rod(t):
        if t < t_onset:
            return baseline
        extra = min(withdrawal_rate * (t - t_onset) * PCM, max_withdrawal * PCM)
        return baseline + extra

    return rho_rod, lambda t: 0.30, "rod_withdrawal", "CH09"


def anomaly_doppler_drift(duration=7200.0, t_onset=1800.0,
                           drift_rate=0.5, rng=None, **kw):
    """Apparent fuel temperature drift causes unnecessary rod compensation. GT: CH08/CH10."""
    baseline = _get_baseline()
    from .params import ALPHA_DOPPLER

    def rho_rod(t):
        if t < t_onset:
            return baseline
        apparent_drift = drift_rate * (t - t_onset)
        compensation = -ALPHA_DOPPLER * apparent_drift * 0.3
        return baseline + compensation

    return rho_rod, lambda t: 0.30, "doppler_drift", "CH08"


def anomaly_correlated(duration=7200.0, t_onset=1800.0,
                        delta_void=0.10, rng=None, **kw):
    """Void rise + under-compensating rod response. GT: CH03 (primary), CH09 (secondary)."""
    baseline = _get_baseline()
    NOMINAL_VOID = 0.30

    void_fn = _piecewise([
        (0.0,            NOMINAL_VOID),
        (t_onset,        NOMINAL_VOID),
        (t_onset + 120,  NOMINAL_VOID + delta_void),
        (duration,       NOMINAL_VOID + delta_void),
    ])

    def rho_rod(t):
        if t < t_onset:
            return baseline
        expected = delta_void * 100.0 * 10.0 * PCM
        return baseline - expected * 0.40 * min((t - t_onset) / 300.0, 1.0)

    return rho_rod, void_fn, "correlated_void_rod", "CH03"


def apply_sensor_corruption(telemetry, channel, corruption_type,
                             t_onset, rng, **kwargs):
    """Add sensor-level corruptions (dropout, drift, spike) — post-processing only."""
    import copy
    tel = copy.deepcopy(telemetry)
    t   = tel["t"]
    sig = tel[channel].copy()
    mask = t >= t_onset

    if corruption_type == "dropout":
        sig[mask] = np.nan
    elif corruption_type == "drift":
        rate = kwargs.get("rate", 0.001)
        sig[mask] += rate * (t[mask] - t_onset)
    elif corruption_type == "spike":
        prob  = kwargs.get("prob", 0.02)
        scale = kwargs.get("scale", 0.1 * float(np.nanstd(sig)))
        idx   = np.where(mask)[0]
        hit   = rng.random(len(idx)) < prob
        sig[idx[hit]] += rng.normal(0, scale, int(hit.sum()))

    tel[channel] = sig
    return tel


SCENARIO_CATALOGUE = {
    "normal":              normal_operation,
    "void_spike":          anomaly_void_spike,
    "xenon_pit":           anomaly_xenon_pit,
    "rod_withdrawal":      anomaly_rod_withdrawal,
    "doppler_drift":       anomaly_doppler_drift,
    "correlated_void_rod": anomaly_correlated,
}
