# Simulator Design Note (v0.1 — first pass, NOT FROZEN)

**Status: DRAFT.** This is a first-pass structural specification, written to be
reviewed at the Phase 4 / Step 4 domain sanity check. Numeric parameter
values are intentionally left as `[TBD: confirm from <source>]` placeholders
rather than filled in from memory — every numeric value must be pulled
directly from the cited source and recorded with enough detail (table/
equation reference) that it can be checked. **Do not write simulator code
against this version until Section 4 (reconciliation) and Section 6 (frozen
parameter table) are completed and reviewed.**

This note is the single most important artifact in the project (per
`ROADMAP.md` Section 4.1) — everything downstream depends on it.

---

## 1. Scope and composite structure

Per `LIMITATIONS.md` Section 1, this is **not** a novel simulator. It is an
assembly of existing, cited, peer-reviewed formulations:

| Component | Source | Provides |
|---|---|---|
| Overall RBMK structure, xenon-stability framing | B1 | The "shape" of the model — what an RBMK-class point-kinetics-plus-xenon model needs to capture, and the kind of stability analysis it should support |
| Six-group delayed-neutron point kinetics | B2 and/or B3 | The core ODE system: `dP/dt` and `dC_i/dt` for i=1..6 |
| Xe-135 / I-135 coupling | B4 | `dI/dt` and `dXe/dt`, and the resulting `rho_xenon(t)` |
| Void-coefficient calibration | B8, B9 (cross-checked against B6) | Sign and magnitude of `alpha_void`, i.e. `rho_void(t) = alpha_void * phi(t)` |
| Doppler/graphite-temperature feedback structure | B3 | Form of `rho_doppler(t)`, not its RBMK-specific magnitude |

All variables referenced below are defined in
`/literature/variable_registry.csv`.

## 2. Governing equations (structural form)

### 2.1 Point kinetics (six delayed-neutron groups)

```
dP/dt    = [ (rho(t) - beta) / Lambda ] * P(t)  +  sum_{i=1}^{6} lambda_i * C_i(t)
dC_i/dt  = (beta_i / Lambda) * P(t)  -  lambda_i * C_i(t)        for i = 1..6
```

Source: standard six-group point-kinetics form, per B2/B3. `Lambda`, `beta`,
`beta_i`, `lambda_i` are simulator parameters — see Section 6.

### 2.2 Reactivity decomposition

```
rho(t) = rho_rod(t) + rho_void(t) + rho_doppler(t) + rho_xenon(t)
```

Each term is computed independently and **logged separately** in the
synthetic dataset generation step — this decomposition is what allows Step 7
to tag each injected anomaly with a "ground-truth driving variable"
(per `ROADMAP.md` Section 4.2), which in turn is what Step 11's
interpretability validation checks against.

### 2.3 Xe-135 / I-135 coupling

```
dI/dt  = gamma_I  * Sigma_f * Phi(t)  -  lambda_I * I(t)
dXe/dt = gamma_Xe * Sigma_f * Phi(t)  +  lambda_I * I(t)  -  lambda_Xe * Xe(t)  -  sigma_Xe * Xe(t) * Phi(t)

rho_xenon(t) = - sigma_Xe * Xe(t) * Phi(t) / (normalization term, TBD)
```

Source: B4. `Phi(t)` is neutron flux (related to `P(t)` via normalization —
TBD). `gamma_I`, `gamma_Xe`, `sigma_Xe`, `lambda_I`, `lambda_Xe` are
parameters — see Section 6. `lambda_I` and `lambda_Xe` are well-established
physical decay constants (I-135 and Xe-135 half-lives) and are **low-risk**
to freeze early; `sigma_Xe`, `gamma_I`, `gamma_Xe` need confirmation against
B4's specific derivation (see Variable Registry notes).

### 2.4 Void reactivity feedback

```
rho_void(t) = alpha_void * phi(t)
```

Source: B8/B9 for `alpha_void` (sign **positive** for RBMK at low ORM — this
is the model's most safety-relevant parameter). `phi(t)` (void fraction) is
a **scenario-driven input** in the first-pass model (see Section 5), not
derived from a full thermal-hydraulics solve — full thermal-hydraulics is
out of scope per `LIMITATIONS.md` Section 7.

### 2.5 Doppler / fuel-temperature feedback

```
rho_doppler(t) = alpha_doppler * (T_fuel(t) - T_fuel_nominal)
T_fuel(t): simplified lumped first-order response to P(t) (single time
constant, TBD)
```

Source: structural form from B3. `alpha_doppler` magnitude for graphite is
**not** assumed to transfer directly from B3's gas-cooled reference — flagged
for Phase 4 review.

## 3. Control-rod input and scenario design

`rho_rod(t)` is **not** a free state variable — it is a scenario script
(normal-operation profile + anomaly injection), consistent with the project
being a comparative anomaly-detection study rather than a control-system
simulation. Two scenario classes are anticipated:

- **Normal operation**: small rod adjustments around a setpoint, ORM held
  within normal range (ORM treated as a fixed scenario parameter, not a
  state variable — see Variable Registry).
- **Anomaly classes** (per `ROADMAP.md` Step 7): sensor drift, dropout,
  step changes, oscillatory instabilities, correlated multi-channel faults —
  each implemented as a perturbation to one or more of `rho_rod`, `phi`,
  `Xe`, or a sensor-side corruption of the reported channel (distinct from a
  physical perturbation — important for the "robustness to missing/irregular
  data" engineering axis).

**Explicitly excluded** (per Validation Registry V04 / `LIMITATIONS.md`
Section 4): any scenario representing the AZ-5 positive-scram /
graphite-displacer transient. No anomaly class may be constructed that models
control rods *inserting positive reactivity*.

## 4. REQUIRED reconciliation: delayed-neutron fraction (Keepin-1965 vs. RBMK burnup)

**This section must be completed before Section 6 is frozen.**

The standard six-group `beta_i` / `lambda_i` table (Keepin, 1965) is derived
for thermal fission of U-235. RBMK fuel reaches significant burnup with
substantial Pu-239/241 content, which has a measurably different (typically
lower) effective delayed-neutron fraction `beta`. Educational RBMK simulators
identified during the literature review use a reduced `beta` to account for
this.

Options to resolve (pick one, document the choice and its source):

1. Use B2 or B3's `beta_i`/`lambda_i` table as-is, with an explicit
   limitations statement that this represents a "fresh fuel" approximation
   and may overstate the prompt-criticality margin relative to a burnt RBMK
   core. **Lowest implementation effort, weakest physical fidelity.**
2. Apply a single scalar correction factor to `beta` (sourced from a
   burnup-dependent delayed-neutron fraction table, if one can be found and
   cited), leaving `beta_i`/`lambda_i` group *shapes* from B2/B3 but rescaling
   their sum to match the corrected `beta`. **Moderate effort, requires
   finding a citable correction factor.**
3. Find a six-group table specifically derived for a Pu-bearing / mixed-oxide
   or burnt-fuel composition and use it directly, replacing B2/B3's table
   entirely. **Highest fidelity, highest effort, may not exist as a clean
   citable source.**

**Recommendation for Phase 4 discussion: Option 1, stated explicitly as a
limitation**, since the project's framing already accepts point-kinetics and
lumped thermal-hydraulics as simplifications (`LIMITATIONS.md` Section 7), and
a stated "fresh-fuel approximation" limitation is honest and low-risk. Option
2 is the fallback if a reviewer (internal or external) considers Option 1
insufficient. Option 3 is not recommended given effort vs. expected fidelity
gain for a comparative engineering study.

## 5. Numerical scheme

- Six-group point kinetics with large/step reactivity insertions can be
  numerically stiff. B3 uses a Pade-approximation scheme specifically to
  handle this robustly — **adopt the same numerical approach** (or an
  equivalent stiff ODE solver, e.g. implicit Runge-Kutta / `scipy`'s `LSODA`,
  with the Pade scheme as a documented fallback/cross-check for validation).
- Time step: `[TBD — choose based on the fastest relevant timescale, likely
  the prompt-neutron generation time Lambda; confirm against B2/B3]`.

## 6. Frozen parameter table (TO BE COMPLETED)

**This table is empty by design.** Each row must be filled in by reading the
cited source directly, then reviewed at Step 4 before being marked FROZEN.
Once a row is FROZEN, changing it requires an independent literature
justification per `LIMITATIONS.md` Section 3/Section 7, logged in this file's
revision history (Section 8).

| Parameter | Symbol | Value | Source (table/eq. ref.) | Status |
|---|---|---|---|---|
| Total delayed-neutron fraction | beta | TBD | TBD (depends on Section 4 decision) | NOT FROZEN |
| Group fractions | beta_1..beta_6 | TBD | TBD | NOT FROZEN |
| Group decay constants | lambda_1..lambda_6 | TBD | TBD | NOT FROZEN |
| Prompt neutron generation time | Lambda | TBD | TBD (graphite-moderated value from B3) | NOT FROZEN |
| I-135 decay constant | lambda_I | TBD | Standard physical constant — low risk | NOT FROZEN |
| Xe-135 decay constant | lambda_Xe | TBD | Standard physical constant — low risk | NOT FROZEN |
| I-135 yield fraction | gamma_I | TBD | B4 | NOT FROZEN |
| Xe-135 yield fraction | gamma_Xe | TBD | B4 | NOT FROZEN |
| Xe-135 absorption cross-section | sigma_Xe | TBD | B4 | NOT FROZEN |
| Void reactivity coefficient | alpha_void | TBD (sign: POSITIVE) | B8, cross-check B9 | NOT FROZEN — highest scrutiny |
| Doppler reactivity coefficient | alpha_doppler | TBD | B3 (structural form only — magnitude needs RBMK-appropriate source) | NOT FROZEN |
| Fuel temperature time constant | tau_fuel | TBD | TBD | NOT FROZEN |

## 7. Mapping to Validation Registry

| Validation ID | Test | Which equation(s) it exercises |
|---|---|---|
| V01 | Xenon buildup -> delayed power recovery | Section 2.3 (Xe/I coupling) + Section 2.2 (rho_xenon term) |
| V02 | Positive void insertion -> positive power response | Section 2.4 (rho_void) + Section 2.1 |
| V03 | Control rod insertion -> negative reactivity response | Section 2.2 (rho_rod term) + Section 2.1 |
| V04 | AZ-5/positive-scram transient | NOT MODELED — confirm no code path in Section 3 can produce this |

Every row in Section 6, once filled, should be traceable to at least one of
V01–V03 (V04 is a negative check — confirming absence, not presence).

## 8. Revision history

| Date | Change | Justification | Logged by |
|---|---|---|---|
| (this draft) | Initial structural draft, v0.1 | N/A — first pass | — |

---

## Open items for Phase 4 / Step 4 sanity check

1. Resolve Section 4 (delayed-neutron fraction reconciliation) — recommend
   Option 1.
2. Fill in Section 6 parameter table from B2/B3/B4/B8/B9 directly (not from
   memory or secondary sources).
3. Confirm `alpha_void` sign and magnitude against both B8 and B9 — this is
   the highest-scrutiny parameter.
4. Confirm graphite-appropriate `alpha_doppler` magnitude — B3's value is for
   a gas-cooled reference design and may not transfer directly.
5. Confirm numerical scheme (Section 5) is adequate for the stiffness
   introduced by the chosen `alpha_void` magnitude.
6. Confirm no scenario construction in Section 3 can represent the AZ-5
   transient (V04).
