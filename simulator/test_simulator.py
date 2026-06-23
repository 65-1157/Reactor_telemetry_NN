"""
test_simulator.py — Unit tests for the RBMK-class simulator
=============================================================
Maps directly to the Validation Registry (V01-V04) and the D7-A
inhour-equation benchmark. Run with:

    python -m pytest simulator/test_simulator.py -v

or directly:

    python simulator/test_simulator.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pytest

from rbmk_sim.simulator import Simulator
from rbmk_sim.params    import BETA_TOTAL, PCM, ALPHA_VOID, ALPHA_DOPPLER
from rbmk_sim import params as P
from rbmk_sim.feedback  import (
    void_reactivity, doppler_reactivity, xenon_reactivity, total_reactivity,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture(scope="module")
def sim():
    return Simulator(dt=10.0)


# ============================================================
# Feedback unit tests
# ============================================================

class TestFeedback:

    def test_void_positive_sign(self):
        """Positive void coefficient: more void -> more positive reactivity."""
        r0 = void_reactivity(0.0)
        r1 = void_reactivity(0.5)
        assert r1 > r0, "Void reactivity must be positive for positive void coefficient"

    def test_void_zero_at_zero(self):
        assert abs(void_reactivity(0.0)) < 1e-12

    def test_void_linearity(self):
        """rho_void should be linear in void fraction (linear coefficient model)."""
        r1 = void_reactivity(0.2)
        r2 = void_reactivity(0.4)
        assert abs(r2 / r1 - 2.0) < 1e-9

    def test_doppler_negative_sign(self):
        """Doppler: hotter fuel -> more negative reactivity."""
        r_hot  = doppler_reactivity(1200.0)
        r_cold = doppler_reactivity(800.0)
        assert r_hot < r_cold, "Doppler reactivity must decrease with temperature"

    def test_doppler_zero_at_nominal(self):
        from rbmk_sim.params import T_FUEL_NOMINAL
        assert abs(doppler_reactivity(T_FUEL_NOMINAL)) < 1e-12

    def test_xenon_negative(self):
        """Xenon reactivity is always negative (poison effect)."""
        rxe = xenon_reactivity(1.0)
        assert rxe < 0, "Xenon reactivity must be negative"

    def test_total_reactivity_decomposition(self):
        """Sum of components should equal total."""
        rtot, rrod, rvoid, rdop, rxe = total_reactivity(
            rho_rod=0.001, void_frac=0.30, T_fuel=920.0, Xe_norm=1.0
        )
        assert abs(rtot - (rrod + rvoid + rdop + rxe)) < 1e-12


# ============================================================
# Parameter sanity tests
# ============================================================

class TestParams:

    def test_beta_sum(self):
        """Total beta should match sum of group betas (within float precision)."""
        assert abs(P.BETA_TOTAL - P.BETA_GROUP.sum()) < 1e-9

    def test_beta_in_range(self):
        """Beta_total for thermal U-235 is ~0.0064-0.0065."""
        assert 0.0060 < P.BETA_TOTAL < 0.0070

    def test_n_groups(self):
        assert len(P.BETA_GROUP) == 6
        assert len(P.LAMBDA_GROUP) == 6

    def test_void_coeff_positive(self):
        """RBMK void coefficient must be positive (design constraint)."""
        assert P.ALPHA_VOID > 0, "RBMK void coefficient must be positive"

    def test_doppler_coeff_negative(self):
        """Doppler coefficient must always be negative (stability requirement)."""
        assert P.ALPHA_DOPPLER < 0

    def test_lambda_I_Xe_physical(self):
        """Decay constants should match standard nuclear data (within 1%)."""
        assert abs(P.LAMBDA_I  - 2.90e-5) / 2.90e-5 < 0.01
        assert abs(P.LAMBDA_XE - 2.10e-5) / 2.10e-5 < 0.01

    def test_sigma_Xe_order(self):
        """sigma_Xe should be in the millions-of-barns range."""
        sigma_barns = P.SIGMA_XE * 1e24    # convert cm^2 to barns
        assert 1e6 < sigma_barns < 1e7, f"sigma_Xe={sigma_barns:.2e} barns out of expected range"

    def test_n_channels(self):
        assert P.N_CHANNELS == 10


# ============================================================
# ODE integration tests
# ============================================================

class TestODE:

    def test_steady_state_stable(self, sim):
        """Normal operation at P=1 should stay near P=1 over 1 hour."""
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        P_arr  = result["telemetry"][:, 0]   # CH01
        # Allow small drift from sinusoidal rod perturbation
        assert P_arr.min() > 0.90, "Power dropped too far in normal operation"
        assert P_arr.max() < 1.10, "Power rose too far in normal operation"

    def test_output_shape(self, sim):
        """Telemetry array must have shape (N_t, 10)."""
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        X = result["telemetry"]
        assert X.ndim == 2
        assert X.shape[1] == 10

    def test_no_nan_in_normal(self, sim):
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        assert not np.any(np.isnan(result["telemetry"]))

    def test_tau_fuel_sensitivity(self, sim):
        """
        D6-B sensitivity test: varying tau_fuel from 5 to 30 s should not
        materially change anomaly signals on a 2-hour timescale.
        'Material' defined as > 5% difference in peak xenon reactivity.
        """
        from rbmk_sim import params as _P
        import rbmk_sim.kinetics as _K

        original_tau = _P.TAU_FUEL
        results = {}

        for tau in [5.0, 15.0, 30.0]:
            _P.TAU_FUEL = tau
            # re-import to pick up new value
            import importlib
            import rbmk_sim.kinetics as _K2
            importlib.reload(_K2)
            r = sim.run_scenario("xenon_pit", duration=7200.0, seed=0)
            results[tau] = r["telemetry"][:, 4].min()   # CH05 min xenon reactivity

        _P.TAU_FUEL = original_tau   # restore

        # Check relative variation across tau values is < 5%
        vals = list(results.values())
        variation = (max(vals) - min(vals)) / abs(np.mean(vals))
        assert variation < 0.05, (
            f"tau_fuel sensitivity too high: {variation*100:.1f}% variation "
            f"across tau=[5,15,30]s — investigate fuel temperature model"
        )


# ============================================================
# Validation Registry V01-V04
# ============================================================

class TestValidationRegistry:

    def test_V01_xenon_buildup(self, sim):
        """V01: Xenon builds up after power reduction (iodine pit)."""
        assert sim.validate_V01_xenon_buildup()

    def test_V02_void_positive_power(self, sim):
        """V02: Positive void insertion causes power increase."""
        assert sim.validate_V02_void_positive_power()

    def test_V03_rod_insertion_negative(self, sim):
        """V03: Negative rod reactivity causes power decrease."""
        assert sim.validate_V03_rod_insertion_negative()

    def test_V04_no_positive_scram(self, sim):
        """V04: No scenario produces positive rod reactivity (AZ-5 excluded)."""
        assert sim.validate_V04_no_positive_scram()


# ============================================================
# D7-A Inhour equation benchmark
# ============================================================

class TestInhourBenchmark:

    def test_inhour_half_beta(self, sim):
        """D7-A: Period at rho=0.5*beta matches analytic inhour equation <5%."""
        assert sim.validate_inhour_benchmark(rho_ins=0.5)

    def test_inhour_quarter_beta(self, sim):
        """D7-A: Period at rho=0.25*beta matches analytic inhour equation <5%."""
        assert sim.validate_inhour_benchmark(rho_ins=0.25)


# ============================================================
# Scenario catalogue tests
# ============================================================

class TestScenarios:

    @pytest.mark.parametrize("name", [
        "normal", "void_spike", "xenon_pit",
        "rod_withdrawal", "doppler_drift", "correlated_void_rod",
    ])
    def test_scenario_runs_without_error(self, sim, name):
        result = sim.run_scenario(name, duration=3600.0, seed=42)
        assert "telemetry" in result
        assert result["telemetry"].shape[1] == 10

    def test_anomaly_flag_set(self, sim):
        """All non-normal scenarios should have anomaly=True."""
        for name in ["void_spike", "xenon_pit", "rod_withdrawal",
                     "doppler_drift", "correlated_void_rod"]:
            result = sim.run_scenario(name, duration=3600.0, seed=0)
            assert result["meta"]["anomaly"] is True, f"{name} should have anomaly=True"

    def test_normal_flag_clear(self, sim):
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        assert result["meta"]["anomaly"] is False

    def test_ground_truth_channel_set(self, sim):
        """Each anomaly scenario should name a ground-truth channel."""
        for name in ["void_spike", "xenon_pit", "rod_withdrawal",
                     "doppler_drift", "correlated_void_rod"]:
            result = sim.run_scenario(name, duration=3600.0, seed=0)
            assert result["meta"]["gt_channel"] is not None


# ============================================================
# Sensor corruption tests
# ============================================================

class TestSensorCorruption:

    def test_dropout_produces_nan(self, sim):
        from rbmk_sim.scenarios import apply_sensor_corruption
        import numpy as np
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        raw = result["raw"]
        corrupted = apply_sensor_corruption(
            raw, channel="P", corruption_type="dropout",
            t_onset=1800.0, rng=np.random.default_rng(0)
        )
        assert np.any(np.isnan(corrupted["P"]))
        assert not np.any(np.isnan(raw["P"]))  # original unchanged

    def test_drift_increases_signal(self, sim):
        from rbmk_sim.scenarios import apply_sensor_corruption
        result = sim.run_scenario("normal", duration=3600.0, seed=0)
        raw = result["raw"]
        corrupted = apply_sensor_corruption(
            raw, channel="P", corruption_type="drift",
            t_onset=1800.0, rng=np.random.default_rng(0), rate=0.001
        )
        # After onset, signal should be higher on average
        t = raw["t"]
        mask = t > 1800.0
        assert corrupted["P"][mask].mean() > raw["P"][mask].mean()


# ============================================================
# Standalone runner (no pytest)
# ============================================================

if __name__ == "__main__":
    print("\n=== Running simulator tests standalone ===\n")
    sim = Simulator(dt=10.0)
    sim.run_all_validations()
    sim.validate_inhour_benchmark(rho_ins=0.5)
    sim.validate_inhour_benchmark(rho_ins=0.25)
    print("\nAll done. Run with pytest for full structured output.")
