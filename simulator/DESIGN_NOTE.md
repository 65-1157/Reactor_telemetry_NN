# Simulator Design Note (v0.1, rev. 1 — first pass, NOT FROZEN)

**Status: DRAFT.** This is a first-pass structural specification, written to
be reviewed at the Phase 4 / Step 4 domain sanity check. Section 6 now
contains **provisional values** for parameters that are well-established,
widely-reproduced reactor-physics constants (six-group delayed-neutron data,
I-135/Xe-135 decay constants and yields, Xe-135 cross-section) — these are
explicitly marked "PROVISIONAL (textbook standard)" and still need
confirmation against B2/B3/B4 at Step 4. The RBMK-specific and
safety-critical parameters (`alpha_void`, `alpha_doppler`, `Lambda`,
`tau_fuel`) remain genuinely **TBD** and must be read directly from B3/B8/B9
— these are not estimated or guessed anywhere in this document. **Do not
write simulator code against this version until the TBD rows in Section 6
and the reconciliation in Section 4 are completed and reviewed.**

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
| Total delayed-neutron fraction | beta | approx 0.00645 (see 6.1) | Lamarsh/Keepin thermal U-235; depends on Section 4 decision | PROVISIONAL (textbook standard) |
| Group fractions | beta_1..beta_6 | see 6.1 | Lamarsh/Keepin thermal U-235 | PROVISIONAL (textbook standard) |
| Group decay constants | lambda_1..lambda_6 | see 6.1 | Lamarsh/Keepin thermal U-235 | PROVISIONAL (textbook standard) |
| Prompt neutron generation time | Lambda | order 1e-3 s (graphite-moderated reactors are reported in the ~1e-3 s range, vs. ~1e-4 to 1e-5 s for LWRs) | General reactor-physics reference; exact value TBD from B3 | TBD (RBMK-specific) |
| I-135 decay constant | lambda_I | approx 2.9e-5 s^-1 (half-life approx 6.6 h) | Standard nuclear data | PROVISIONAL (textbook standard) |
| Xe-135 decay constant | lambda_Xe | approx 2.1e-5 s^-1 (half-life approx 9.1 h) | Standard nuclear data | PROVISIONAL (textbook standard) |
| I-135 cumulative fission yield | gamma_I | order 0.06 (approx 6% per fission, thermal U-235) | Standard nuclear data; confirm against B4's specific value | PROVISIONAL (textbook standard) |
| Xe-135 direct fission yield | gamma_Xe | order 0.003 (approx 0.3% per fission - most Xe-135 arises via I-135 decay, not direct yield) | Standard nuclear data; confirm against B4's specific value | PROVISIONAL (textbook standard) |
| Xe-135 thermal absorption cross-section | sigma_Xe | order 1e6 barns (Xe-135 has an unusually large thermal absorption cross-section, commonly cited around 2-3 million barns) | Standard nuclear data; confirm against B4's specific value and units convention | PROVISIONAL (textbook standard) |
| Void reactivity coefficient | alpha_void | TBD (sign: POSITIVE). Candidate magnitudes from Variable Registry: approx 0.03 (B8, approx 0.3 mk per pct void, higher near core axis) vs. commonly cited pre-accident approx 4.7*beta, post-modification approx 0.7*beta (B9) | B8, cross-check B9 - units/conventions differ between sources and must be reconciled, not averaged | TBD (RBMK-specific) - highest scrutiny |
| Doppler reactivity coefficient | alpha_doppler | TBD | B3 (structural form only - magnitude is for a gas-cooled reference design and is NOT assumed to transfer to graphite/RBMK) | TBD (RBMK-specific) |
| Fuel temperature time constant | tau_fuel | TBD | TBD | TBD (RBMK-specific) |

**Note on alpha_void**: B8's figure (approx 0.03) and B9's figure (approx
4.7*beta pre-accident) are given in different unit conventions (a fractional
reactivity-per-void-fraction term vs. a multiple of beta) and are **not**
straightforwardly the same quantity expressed two ways - reconciling these
into a single consistent `alpha_void` for Section 2.4 is itself a Step 4
task, not a simple unit conversion to be done casually. Until reconciled,
this row stays TBD regardless of how plausible either individual figure
looks in isolation.

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
| (this draft, rev. 1) | Section 6 populated with PROVISIONAL standard textbook values for six-group delayed-neutron data, lambda_I, lambda_Xe, gamma_I, gamma_Xe, sigma_Xe, and an order-of-magnitude placeholder for Lambda. alpha_void, alpha_doppler, tau_fuel remain TBD (RBMK-specific). | Standard, widely-reproduced reactor-physics reference values (Lamarsh/Keepin) — used as a documented starting point pending Step 4 confirmation against B2/B3/B4. No RBMK-specific or Chernobyl-specific values introduced. | — |

---

## Open items for Phase 4 / Step 4 sanity check

1. Resolve Section 4 (delayed-neutron fraction reconciliation) — recommend
   Option 1, using the Section 6.1 table as the fresh-fuel approximation.
2. Confirm whether B2 and/or B3 reproduce the Section 6.1 table directly or
   specify a variant; if a variant, use it consistently (no mixing).
3. Read B3 directly to replace the order-of-magnitude `Lambda` placeholder
   with a specific graphite-moderated value.
4. Read B4 directly to confirm `gamma_I`, `gamma_Xe`, `sigma_Xe` against the
   PROVISIONAL standard values and units convention used in Section 2.3.
5. **Read B8 and B9 directly to resolve `alpha_void`** — this is the
   highest-scrutiny item. The two candidate figures use different unit
   conventions and must be reconciled into one consistent value for
   Section 2.4, not averaged or guessed.
6. Read B3 to determine whether its `alpha_doppler` structural form can be
   adapted with an RBMK-appropriate magnitude, or whether an alternative
   graphite-specific source is needed.
7. Confirm numerical scheme (Section 5) is adequate for the stiffness
   introduced by the chosen `alpha_void` magnitude, once resolved.
8. Confirm no scenario construction in Section 3 can represent the AZ-5
   transient (V04).
