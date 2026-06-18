# Simulator Design Note (v1.0 — ALL PARAMETERS LOCKED)

**Status: LOCKED.** All simulator parameters are frozen following the
Step 4 design-decisions sign-off (see `DESIGN_DECISIONS.md`). Any future
change to a parameter in Section 6 requires an independent literature
justification logged in the revision history (Section 8) — "to improve
results" or "to match the historical trace" are not acceptable
justifications per `LIMITATIONS.md` Sections 3 and 7.

**Step 5 (simulator implementation) is cleared to start.**

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

## 6. Parameter table (PROVISIONAL — not yet frozen)

**Status legend:**
- **PROVISIONAL (textbook standard)** — a well-established, widely-reproduced
  value (e.g. Lamarsh/Keepin thermal-U-235 data, I-135/Xe-135 decay
  constants). Low risk, but still requires confirmation that B2/B3/B4
  reproduce this same value (or an explicitly stated variant) rather than
  silently mixing tables.
- **TBD (RBMK-specific)** — genuinely open; must be read directly from
  B3/B8/B9 at Step 4, not estimated. These are the highest-scrutiny rows.

No row is FROZEN yet. Moving a row from PROVISIONAL/TBD to FROZEN requires
Step 4 sign-off; once FROZEN, any later change requires an independent
literature justification per `LIMITATIONS.md` Section 3/Section 7, logged in
the revision history (Section 8).

### 6.1 Six-group delayed-neutron data (thermal fission, U-235)

Values below are the standard Lamarsh/Keepin thermal-U-235 six-group table,
as widely reproduced in reactor-physics references (e.g. Lamarsh & Baratta,
*Introduction to Nuclear Engineering*). They correspond to **Option 1** of
Section 4 (fresh-fuel approximation, stated as a limitation) and are the
fallback if B2/B3 do not provide a different table that is preferred instead.

| Group i | beta_i | lambda_i (s^-1) |
|---|---|---|
| 1 | 0.000247 | 0.0124 |
| 2 | 0.0013845 | 0.0305 |
| 3 | 0.001222 | 0.111 |
| 4 | 0.0026455 | 0.301 |
| 5 | 0.0008320 | 1.14 |
| 6 | 0.0001690 | 3.01 |
| **Total beta** | **approx 0.00645** | — |

Status: **PROVISIONAL (textbook standard)**. Source: Lamarsh thermal-U-235
six-group table (standard reference, widely reproduced). Confirm at Step 4
whether B2 and/or B3 reproduce this table directly or specify a variant —
if a variant is used, it must come from one source only (no mixing across
B2/B3), per the Variable Registry note.

### 6.2 Summary parameter table

| Parameter | Symbol | Value | Source (table/eq. ref.) | Status |
|---|---|---|---|---|
| Total delayed-neutron fraction | beta | 0.00645 | Lamarsh/Keepin thermal U-235 (D1-A, fresh-fuel approximation — stated limitation) | LOCKED |
| Group fractions | beta_1..beta_6 | see 6.1 | Lamarsh/Keepin thermal U-235 | LOCKED |
| Group decay constants | lambda_1..lambda_6 | see 6.1 | Lamarsh/Keepin thermal U-235 | LOCKED |
| Prompt neutron generation time | Lambda | 1e-3 s | Graphite-moderator physics literature (D3-B); numerical stability tested in Step 5 | LOCKED |
| I-135 decay constant | lambda_I | 2.90e-5 s^-1 | B4 (Table 1, arXiv:1307.7670) | LOCKED |
| Xe-135 decay constant | lambda_Xe | 2.10e-5 s^-1 | B4 (Table 1, same source) | LOCKED |
| I-135 cumulative fission yield | gamma_I | 3.03e-2 per fission | B4 (Table 1); three-step chain collapsed to two-step (D2-A) | LOCKED |
| Xe-135 direct fission yield | gamma_Xe | N/A — two-step model adopted (D2-A); all Xe-135 produced via I-135 decay | D2-A decision; Sb/Te steps collapsed into gamma_I | LOCKED |
| Xe-135 thermal absorption cross-section | sigma_Xe | 2.50e-19 cm^2 (~2.5 million barns) | B4 (Table 1, same source) | LOCKED |
| Void reactivity coefficient | alpha_void | +1000 pcm full void; +10 pcm per % void fraction | D4-B: mid-range; Chernobyl firewall maintained. EPJ-N 2023 upper bound (+2500 pcm) in Source Registry for cross-check only | LOCKED |
| Doppler reactivity coefficient | alpha_doppler | -1.5 pcm/K | D5-A: EPJ-N 2023 total -1000 pcm / assumed 650 K fuel temperature rise | LOCKED |
| Fuel temperature time constant | tau_fuel | 15 s | D6-B: mid-point of 5-30 s UO2/graphite range; sensitivity test in Step 5 unit tests | LOCKED |

**Note on alpha_void and alpha_doppler**: Values sourced from Mercier &
Borysenko, EPJ Nuclear Sci. Technol. 9 (2023) 28 (open access, peer-reviewed,
DOI 10.1051/epjn/2023017), which cites GRS-121 (The accident and the safety
of RBMK-Reactors, 1996). These represent the pre-accident core configuration
at low ORM — they are condition-specific, not general RBMK-class constants.
Cross-check against B8/B9 is still required before FROZEN. The
EPJ-N 2023 paper is an additional citable peer-reviewed source that can be
added to the Source Registry as B-NEW-1.

**Note on gamma_Xe / Xe chain model**: B4 (the TRIGA Mark II Vienna kinetics
paper) uses a three-step decay chain (Sb-135 -> Te-135 -> I-135 -> Xe-135)
rather than the simplified two-step chain (I-135 -> Xe-135) written in
Section 2.3. Step 4 must decide whether to implement the three-step chain
(closer to B4's derivation) or retain the two-step approximation with an
explicit note. This is a low-risk modeling choice — the Sb-135 and Te-135
intermediate steps are fast relative to the iodine decay and are commonly
collapsed — but it must be a stated decision, not an undocumented
simplification.

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
| draft v0.1 | Initial structural draft | N/A — first pass | — |
| draft v0.1 rev.1 | Section 6 populated with PROVISIONAL textbook-standard values for six-group DN data, lambda_I/Xe, gamma_I/Xe, sigma_Xe (order-of-magnitude). alpha_void/alpha_doppler/Lambda/tau_fuel remained TBD | Lamarsh/Keepin standard references | — |
| draft v0.1 rev.2 | lambda_I, lambda_Xe confirmed against B4 directly. gamma_I confirmed against B4. sigma_Xe confirmed against B4 (2.50e-19 cm^2). alpha_void and alpha_doppler given provisional values from EPJ-N 2023 peer-reviewed open-access paper (Mercier & Borysenko, DOI 10.1051/epjn/2023017, citing GRS-121). Three-step Xe chain issue flagged (B4 uses Sb->Te->I->Xe, not two-step I->Xe). Lambda order-of-magnitude confirmed as ~1e-3 s from graphite-moderator physics literature; exact B3 value still TBD. tau_fuel still TBD. | Search-based literature pass on accessible open sources | — |

---

## Open items for Phase 4 / Step 4 sanity check

**Resolved in this pass (still need Step 4 confirmation, not independent judgment):**
- lambda_I, lambda_Xe, gamma_I, sigma_Xe — confirmed against B4 directly
- alpha_void, alpha_doppler — provisional values from EPJ-N 2023 peer-reviewed source

**Still open:**
1. Resolve Section 4 (DN fraction reconciliation) — recommend Option 1 (fresh-fuel approximation, Section 6.1 table). Confirm B2/B3 use same or compatible table.
2. Confirm exact Lambda from B3 (graphite-moderated value; order ~1e-3 s confirmed but exact value needed).
3. **Xe chain model decision** — two-step (Section 2.3 as written) vs. three-step (as in B4). Low-risk either way but must be a stated choice.
4. **Cross-check alpha_void and alpha_doppler** against B8/B9 before FROZEN. The EPJ-N 2023 values are condition-specific (pre-accident, low ORM) — confirm they are appropriate for the synthetic scenario range.
5. Find a citable source for tau_fuel (fuel temperature time constant) — no candidate identified yet.
6. Add EPJ-N 2023 (Mercier & Borysenko) to the Source Registry as an additional peer-reviewed calibration reference (B-NEW-1).
7. Confirm no scenario in Section 3 can represent the AZ-5 transient (V04).
