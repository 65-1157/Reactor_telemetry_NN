# Claims Audit Checklist

Used at Step 14 (pre-submission internal claims audit), and as a quick
self-check at any earlier point when drafting text. Each item should be
checked against the **current manuscript draft** (including abstract,
figure/table captions, and supplementary material — not just the body text).

For each item, record: ✅ Pass / ⚠️ Needs rewording / ❌ Fail (must fix before
proceeding), plus the location(s) checked.

## A. Prevention / counterfactual claims

- [ ] No statement implies the system "would have prevented", "could have
      prevented", or "would have avoided" the Chernobyl accident or any
      equivalent real-world event.
- [ ] No statement implies a counterfactual outcome for the historical event
      ("had this system been in place, X would not have happened").

## B. AZ-5 / positive-scram framing

- [ ] No statement implies the AZ-5 positive-scram / graphite-displacer-tip
      effect is addressable, mitigated, or detectable by a monitoring or
      ML/DL layer.
- [ ] The simulator's non-modeling of this effect is stated explicitly as a
      scope decision (cross-check against Validation Registry V04 and
      `LIMITATIONS.md` Section 7).

## C. Quantitative lead-time claims

- [ ] No statement gives a specific time interval ("N minutes before the
      scram") for when the model "would have" detected an anomaly, based on
      the digitized Chernobyl data.
- [ ] Case-study results (Step 13) are described qualitatively
      ("the anomaly score rises in the period associated with X", not
      "the model detects the anomaly N minutes early").

## D. Simulator novelty

- [ ] No statement claims the reactor kinetics simulator, or any of its
      component equations, is a novel contribution of this paper.
- [ ] The simulator is consistently described as an assembly of existing,
      cited formulations (Source Registry B1–B9), per `LIMITATIONS.md`
      Section 1 and the Simulator Design Note.

## E. Architecture novelty

- [ ] No statement claims any of the four compared architectures (LSTM-AE,
      GRU encoder-decoder, CNN/Wavelet, Transformer) is a novel architecture
      proposed by this paper.
- [ ] Each architecture is attributed to its source design (per the
      architecture spec sheets in `/models/specs/`).

## F. Interpretability novelty framing

- [ ] The interpretability contribution is framed as **cross-architecture
      validation of SHAP/attention outputs against known, injected,
      ground-truth anomaly sources within a comparative engineering study** —
      not as "the first application of XAI/SHAP/attention to reactor or
      nuclear telemetry".
- [ ] Related work (A2, A7, and other near-neighbor interpretability papers
      from the Source Registry) is cited and the narrower novelty claim is
      explicitly positioned against them.

## G. Sim-to-real generalization

- [ ] A limitations statement is present that strong performance on the
      literature-derived synthetic dataset is not evidence of performance on
      real plant telemetry of any kind (RBMK or otherwise), independent of
      the Chernobyl framing.

## H. Historical data usage

- [ ] No simulator parameter, dataset generation rule, or model
      hyperparameter is described (even implicitly, e.g. "tuned to better
      reflect the historical trajectory") as derived from the digitized
      Chernobyl data.
- [ ] All simulator parameters trace to Source Registry entries B1–B9 via the
      Variable Registry.
- [ ] Any parameter change made after a Phase 6/9 plausibility check cites an
      independent literature justification (not "to match the historical
      trace") and is logged.

## I. Digitization provenance

- [ ] Every digitized data point used in the case study has documented
      provenance (source, tool, estimated error) per `LIMITATIONS.md`
      Section 6.
- [ ] Any uncorroborated / "ghost reading" point is marked as such or
      excluded — none are used silently.

## J. General tone

- [ ] The paper's framing throughout (title, abstract, introduction,
      conclusion) matches the "Resulting Project Framing" in
      `ROADMAP.md` Section 1.1 — comparative + explainable anomaly detection
      on synthetic RBMK-inspired telemetry, with an illustrative historical
      case study.

---

**Sign-off.** This checklist must be completed with no ❌ items remaining
before the manuscript proceeds to formatting (Step 15). ⚠️ items should be
resolved by rewording, not by reinterpretation of `LIMITATIONS.md`.

| Reviewer | Date | Outcome |
|---|---|---|
| | | |
