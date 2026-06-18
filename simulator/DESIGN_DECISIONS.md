# Pre-Step-5 Design Decisions

**Purpose:** Every decision in this file must be locked — with a chosen
option recorded and initialled — before any simulator code is written
(Step 5). This document is the Step 4 sanity-check checklist. It is also
the record that a reviewer (nuclear-engineering domain, IEEE, or internal
claims audit) can inspect to confirm that no design choice was made
arbitrarily or without a cited basis.

Each decision is presented as: context → options → recommended option →
space for sign-off. Where a decision has already been made in the Design
Note, it is recorded here for completeness and confirmation, not reopened.

---

## D1. Delayed-neutron fraction (beta) — Keepin-1965 vs. RBMK burnup

**Context:** The standard six-group beta_i / lambda_i table (Lamarsh/Keepin,
thermal U-235) gives beta ≈ 0.00645. RBMK fuel at significant burnup
contains Pu-239/241, which has a lower effective delayed-neutron fraction
(literature values for burnt RBMK fuel cluster around beta ≈ 0.005,
consistent with the Rust RBMK-1000 simulator's documented choice of
beta = 0.005 for burned fuel). This matters because beta sets the
prompt-criticality margin — a higher beta makes the simulated reactor
slightly harder to drive prompt-critical than a real burnt RBMK core.

**Options:**
- **D1-A (recommended):** Use the Lamarsh/Keepin thermal-U-235 table
  (beta ≈ 0.00645) as a fresh-fuel approximation. State explicitly in
  LIMITATIONS.md and the paper methodology that this overestimates the
  prompt-criticality margin relative to a burnt RBMK core. Low effort,
  honest, defensible for a comparative engineering study.
- **D1-B:** Apply a scalar correction to beta (e.g. reduce to ≈ 0.005
  citing burnup physics literature), keeping group *shapes* from Keepin
  but rescaling total beta. Requires finding and citing a specific burnup
  correction source.
- **D1-C:** Find and use a six-group table specifically for Pu-bearing
  mixed fuel. Highest fidelity, highest effort, may not exist as a clean
  citable source for RBMK fuel composition.

**Recommended:** D1-A. If Step 4 reviewer considers D1-A insufficient,
fall back to D1-B with the Rust simulator's beta = 0.005 as a secondary
reference (non-peer-reviewed, but documents its own source chain).

| Decision | Chosen option | Justification | Sign-off |
|---|---|---|---|
| D1 | | | |

---

## D2. Xenon decay chain model — two-step vs. three-step

**Context:** Section 2.3 of the Design Note uses a two-step chain
(I-135 → Xe-135). B4 (the TRIGA Mark II Vienna kinetics paper, which is
the primary source for the Xe/I equations) uses a three-step chain:
Sb-135 → Te-135 → I-135 → Xe-135, with Sb-135 yield 1.50e-3 and
Te-135 yield 3.13e-2 per fission. The two extra steps (Sb, Te) have
very short half-lives relative to I-135 (hours) — they are commonly
collapsed into an effective I-135 production term in simplified models.

**Options:**
- **D2-A (recommended):** Use the two-step approximation (I-135 → Xe-135)
  with an effective I-135 fission yield of gamma_I = 3.03e-2 (from B4,
  already in the parameter table). State in the methodology that the
  Sb-135/Te-135 intermediate steps are collapsed per standard point-kinetics
  practice. Low effort, standard simplification, consistent with the
  point-kinetics scope stated in LIMITATIONS.md Section 7.
- **D2-B:** Implement the full three-step chain from B4. Slightly more
  faithful to B4's derivation; adds two state variables (C_Sb, C_Te)
  and two ODEs. Marginal fidelity gain for the timescales relevant to
  anomaly detection (hours), not recommended given the existing
  simplifications already accepted (point kinetics, lumped thermal
  hydraulics).

**Recommended:** D2-A. Update Section 2.3 header to note the collapse.

| Decision | Chosen option | Justification | Sign-off |
|---|---|---|---|
| D2 | | | |

---

## D3. Prompt neutron generation time (Lambda) — exact value

**Context:** Lambda is confirmed at order ~1e-3 s from general
graphite-moderator physics literature. The exact RBMK-1000 value
requires reading B3 (the ScienceDirect 2016 graphite-moderated six-group
PK paper) directly. Lambda affects the prompt-neutron response timescale
but not the slow xenon/iodine dynamics (hours) or the void feedback sign
— it is important for numerical stability of the ODE solver and for the
shape of fast transients, but less critical for the anomaly-detection
scenarios, which operate on minutes-to-hours timescales.

**Options:**
- **D3-A:** Read B3 directly and extract the exact graphite-moderated
  Lambda value. Requires human access to B3.
- **D3-B (fallback):** Use Lambda = 1e-3 s as the working value,
  documented as "consistent with graphite-moderated reactor physics
  literature" with a note that the exact RBMK-1000 value was not
  available in an accessible open source. Acceptable for Step 5 provided
  the ODE solver is tested for numerical stability at this value.

**Recommended:** Attempt D3-A first; use D3-B if B3 is not accessible.
Either way, document the choice and test numerical stability (see D7).

| Decision | Chosen option | Justification / value used | Sign-off |
|---|---|---|---|
| D3 | | | |

---

## D4. Void reactivity coefficient (alpha_void) — freeze and scope

**Context:** Provisional value from EPJ-N 2023 (Mercier & Borysenko,
DOI 10.1051/epjn/2023017): +2500 pcm for full void (100% void fraction),
implying alpha_void ≈ +25 pcm per % void. This is explicitly the
pre-accident, low-ORM Chernobyl-4 configuration — a worst-case RBMK value,
not a general or nominal RBMK operating value. The post-modification
value (B9) is approximately +beta ≈ +0.7*beta, i.e. far lower.

**The synthetic dataset generation (Step 7) will use this coefficient
for anomaly scenario injection — the scope of alpha_void determines
what physical scenarios the model can generate.**

**Options:**
- **D4-A:** Use the pre-accident worst-case value (+2500 pcm full void)
  for anomaly scenarios specifically representing "degraded / low-ORM"
  operating conditions. Use a reduced value (e.g. +500 pcm, consistent
  with more normal RBMK operating conditions and a higher ORM) for
  normal-operation and mild-anomaly scenarios. This gives a two-regime
  model: normal (low void coefficient) and degraded (high void
  coefficient). More realistic scenario taxonomy; slightly more complex
  to implement.
- **D4-B (recommended):** Use a single mid-range value (e.g. +1000 pcm
  full void, between nominal and worst-case) as the fixed simulator
  coefficient, with a stated scope: "representative of RBMK operating
  conditions with reduced but non-zero ORM." Simpler; avoids the
  appearance of specifically calibrating to the Chernobyl configuration
  (consistent with LIMITATIONS.md Section 3 firewall). The +2500 pcm
  figure is retained in the Source Registry as a cross-check upper bound.
- **D4-C:** Use the full +2500 pcm pre-accident value for all scenarios.
  Simplest implementation; most aggressive anomaly signals. Risk: the
  simulator is implicitly tuned toward the Chernobyl configuration, which
  is exactly the firewall LIMITATIONS.md is designed to prevent.

**Recommended:** D4-B. Explicitly chosen to maintain the Chernobyl
firewall. Document clearly in the methodology.

| Decision | Chosen option | Value used (pcm) | Justification | Sign-off |
|---|---|---|---|---|
| D4 | | | | |

---

## D5. Doppler reactivity coefficient (alpha_doppler) — scope

**Context:** Provisional value from EPJ-N 2023: −1000 pcm total Doppler
effect (cited as "Doppler effect brings −1000 pcm", associated with the
same pre-accident configuration as D4). This is a total effect, not a
coefficient per degree K. The Design Note Section 2.5 uses a linear
form: rho_doppler = alpha_doppler * (T_fuel - T_nominal).
Converting −1000 pcm total to a per-K coefficient requires knowing the
fuel temperature range, which is itself a scenario parameter.

**Options:**
- **D5-A (recommended):** Express alpha_doppler in pcm/K and back-calculate
  from the −1000 pcm total using a nominal fuel temperature rise of
  ~500–800 K above inlet (typical for RBMK operating conditions, consistent
  with coolant inlet ~270°C and fuel centerline temperatures in the range
  ~700–1000°C). This gives alpha_doppler in the range −1.25 to −2.0 pcm/K.
  Document the assumed temperature range and flag for Step 4 review.
- **D5-B:** Retain −1000 pcm as a fixed offset (applied at full operating
  power) rather than a per-K coefficient. Simpler; avoids the temperature
  range assumption. Less physically faithful for transients where fuel
  temperature varies significantly.

**Recommended:** D5-A with a stated temperature range assumption, flagged
in the methodology. Exact alpha_doppler value in pcm/K to be confirmed
at Step 4 against B3 or an equivalent graphite-specific source.

| Decision | Chosen option | Value used (pcm/K) | Temperature range assumed | Sign-off |
|---|---|---|---|---|
| D5 | | | | |

---

## D6. Fuel temperature time constant (tau_fuel) — source and value

**Context:** tau_fuel is still TBD — no citable source was identified
in the literature pass. It controls how quickly T_fuel responds to P(t)
in the simplified lumped model (Section 2.5): dT_fuel/dt = (P - T_fuel)
/ tau_fuel (schematic form). For anomaly-detection scenarios on
minutes-to-hours timescales, the exact value of tau_fuel matters less
than for fast transient simulations — but it must still be stated and
justified, not guessed.

**Options:**
- **D6-A:** Attempt to find a graphite/RBMK-appropriate tau_fuel from
  B3 or a thermal-hydraulics reference. Requires human reading pass.
- **D6-B (fallback):** Use a typical thermal time constant for uranium
  oxide fuel in a graphite-moderated channel (commonly cited in the
  range 5–30 seconds for the fuel-to-coolant response), state this
  as an order-of-magnitude engineering approximation, and perform a
  sensitivity test (Step 5 unit tests) to confirm that varying tau_fuel
  within this range does not materially change the anomaly signals on
  the minutes-to-hours timescale.

**Recommended:** D6-B as the default for Step 5, with D6-A as the
preferred outcome if the reading pass (D3) also yields a tau_fuel
value from B3.

| Decision | Chosen option | Value used (s) | Sign-off |
|---|---|---|---|
| D6 | | | |

---

## D7. Numerical scheme — ODE solver choice

**Context:** The six-group point-kinetics system is stiff (the prompt
neutron timescale Lambda ~1e-3 s vs. the xenon timescale ~hours).
Design Note Section 5 recommends a stiff ODE solver (scipy LSODA or
implicit Runge-Kutta), with the Pade-approximation scheme from B3 as
a documented fallback/cross-check. The void reactivity coefficient
magnitude (D4) affects how stiff the system becomes during a positive
void transient.

**Options:**
- **D7-A (recommended):** Use `scipy.integrate.solve_ivp` with
  `method='LSODA'` (automatic stiffness detection, well-suited for
  this ODE system). Set absolute tolerance `atol=1e-8`, relative
  tolerance `rtol=1e-6` as a starting point; adjust if the V01–V03
  validation tests show instability. Validate against an analytic
  step-reactivity solution (standard point-kinetics benchmark) before
  running any anomaly scenarios.
- **D7-B:** Implement the Pade-approximation scheme from B3 directly.
  More faithful to the source; higher implementation effort; primarily
  useful if D7-A shows instability at the chosen alpha_void magnitude.

**Recommended:** D7-A first; D7-B as fallback if instability observed.

| Decision | Chosen option | Tolerances | Validation benchmark | Sign-off |
|---|---|---|---|---|
| D7 | | | | |

---

## D8. Simulator output channels — telemetry variable list

**Context:** The synthetic dataset (Step 7) is multivariate telemetry.
The choice of output channels defines what the DL models see and what
the interpretability layer can attribute anomalies to. The channel list
should be: (a) physically meaningful and consistent with what a real
RBMK-class plant would instrument, (b) sufficient to make each anomaly
class distinguishable (for the ground-truth attribution), and (c) not
so large that it inflates the comparison unfairly.

**Proposed channel list (to confirm at Step 4):**

| Channel | Variable | Anomaly classes it drives |
|---|---|---|
| CH01 | Reactor power P(t) — normalized | All classes |
| CH02 | Total reactivity rho(t) | All classes |
| CH03 | Void fraction phi(t) | Void-driven anomalies (V02-class) |
| CH04 | Void reactivity rho_void(t) | Void-driven anomalies |
| CH05 | Xenon reactivity rho_xenon(t) | Xenon/iodine anomalies (V01-class) |
| CH06 | Xe-135 concentration Xe(t) | Xenon/iodine anomalies |
| CH07 | I-135 concentration I(t) | Xenon/iodine anomalies |
| CH08 | Fuel temperature T_fuel(t) | Doppler-driven anomalies |
| CH09 | Control rod reactivity rho_rod(t) | Rod-withdrawal anomalies (V03-class) |
| CH10 | Doppler reactivity rho_doppler(t) | Fuel-temperature anomalies |

Sensor-corruption channels (for the "robustness to missing/irregular
data" engineering axis) are applied on top of these physical channels
as a post-processing step in dataset generation — they are not additional
simulator state variables.

**Decision required:** Confirm this channel list, add or remove channels,
and confirm that each anomaly class in the taxonomy (Step 7) has at least
one channel as its designated ground-truth driving variable.

| Decision | Channel list confirmed? | Changes | Sign-off |
|---|---|---|---|
| D8 | | | |

---

## D9. CNN/Wavelet architecture variant — still open

**Context:** This is the one architecture whose specific published design
is not yet pinned (per the roadmap open items list). All four architecture
spec sheets (Step 8) must cite a single published design. The
CNN/Wavelet arm is the only one without a citation.

**Candidates identified from the Track A literature review:**

- **D9-A:** 1D CNN autoencoder with multi-scale convolutional filters
  (directly analogous to the LSTM-AE pattern, replaces recurrent with
  convolutional layers). Published variants exist in the general
  industrial time-series anomaly-detection literature — needs a specific
  citation.
- **D9-B:** Wavelet decomposition front-end feeding a shallow
  convolutional autoencoder. Closer to the "wavelet-based" framing in
  the project brief; slightly more complex to implement; provides a
  natural multi-resolution decomposition that is interpretable.
- **D9-C:** MSCRED (Multi-Scale Convolutional Recurrent Encoder-Decoder)
  or similar hybrid. Higher complexity; borderline methods-novelty risk.

**Recommended:** D9-A or D9-B — decision deferred to the architecture
spec freeze (Step 8), but must be resolved before Step 8, not during it.
A candidate citation for D9-A: the CNN-AE variant used in several
SWaT/WADI benchmark papers (e.g. those underlying A9/A10 in the Source
Registry). A candidate for D9-B: any wavelet-decomposition AE from the
process-industry literature.

**Action:** Identify and agree on one specific paper to cite before
Step 8. This does not require a human reading pass — a targeted search
is sufficient.

| Decision | Chosen variant | Citation | Sign-off |
|---|---|---|---|
| D9 | | | |

---

## D10. Reference hardware platform — latency/FLOPs/memory measurement

**Context:** METRICS.md requires that inference latency, FLOPs, and
memory are measured on a single, stated, fixed reference platform.
This needs to be decided before architecture spec sheets are written
(Step 8) and before training begins (Step 9).

**Decision required:**
- CPU-only measurement (more reproducible across readers; lower absolute
  performance; appropriate if the paper frames deployment in
  resource-constrained environments) — e.g. a specific CPU model, fixed
  clock speed, single thread.
- GPU measurement (more relevant for real-time industrial deployment;
  less reproducible; appropriate if the paper frames deployment in
  server/edge-GPU environments) — e.g. a specific GPU model and VRAM.
- Both, with CPU as primary (best of both worlds; slightly more
  reporting overhead).

**Recommended:** Report both, with CPU as primary — this is the most
defensible choice for IEEE Access reviewers who may not have GPU access
to reproduce results, while still being informative for practitioners.
Fix the specific machine configuration (CPU model, RAM, OS, Python/
PyTorch version) in METRICS.md before Step 9.

| Decision | Platform choice | Hardware spec | Sign-off |
|---|---|---|---|
| D10 | | | |

---

## Summary checklist for Step 4 sign-off

| ID | Decision | Status |
|---|---|---|
| D1 | Delayed-neutron fraction table choice | OPEN |
| D2 | Xe chain model (two-step vs three-step) | OPEN |
| D3 | Exact Lambda value | OPEN |
| D4 | alpha_void value and scope | OPEN |
| D5 | alpha_doppler in pcm/K | OPEN |
| D6 | tau_fuel value and source | OPEN |
| D7 | ODE solver choice and tolerances | OPEN |
| D8 | Simulator output channel list | OPEN |
| D9 | CNN/Wavelet architecture variant | OPEN |
| D10 | Reference hardware platform | OPEN |

All ten items must move from OPEN to a signed-off chosen option before
simulator code (Step 5) is written. Items D1–D8 are Step 4 (domain
sanity check) scope. Items D9–D10 are Step 8 scope but are listed here
so they are visible early and not left until the last moment.
