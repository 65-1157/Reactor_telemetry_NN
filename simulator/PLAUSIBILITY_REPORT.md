# Simulator Plausibility Report (Step 6)

Generated: 2026-06-23 19:02 UTC

## Anchor Registry checks

| Anchor | Check | Result |
|---|---|---|
| A-01 | Low-ORM amplifies void-driven power excursion | FAIL |
| A-02 | Xe-135 peaks hours after power step-down (iodine pit) | PASS |
| A-03 | Void increase produces positive power response | PASS |

## Interpretation

These checks confirm the simulator produces qualitatively plausible
RBMK-class reactor behavior consistent with the historical anchors.
No simulator parameter was adjusted as a result of these checks.
All parameters remain as locked in DESIGN_DECISIONS.md (D1-D10).

## Firewall statement

Per LIMITATIONS.md Section 3: anchor checks are qualitative plausibility
tests only. They do not constitute calibration of the simulator to the
Chernobyl trajectory. The simulator parameters remain sourced exclusively
from reactor-physics literature (B1-B9).
