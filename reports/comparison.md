# Harness comparison (NOT LLM results)

`faults` → `control`

- Paired trials: 45 · fail → pass: 45 · pass → fail: 0 · unchanged: 0
- Scenarios that moved: 45 up, 0 down (of 45)
- Change in pass rate: +100% [+100%, +100%], bootstrap over scenarios
- Exact sign test over scenarios: p < 0.001

With 45 scenarios, 6 of them must move the same way before
the sign test can call a difference at 5% — 13% of the suite. Real effects smaller than that exist and this dataset cannot see them.

Pairs share scenario/trial IDs, not necessarily matched model randomness.
