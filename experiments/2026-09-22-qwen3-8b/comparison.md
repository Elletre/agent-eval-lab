# Model comparison

`baseline` → `improved`

- Paired trials: 81 · fail → pass: 19 · pass → fail: 15 · unchanged: 47
- Scenarios that moved: 9 up, 7 down (of 27)
- Change in pass rate: +5% [-12%, +21%], bootstrap over scenarios
- Exact sign test over scenarios: p = 0.804

With 27 scenarios, 6 of them must move the same way before
the sign test can call a difference at 5% — 22% of the suite. Real effects smaller than that exist and this dataset cannot see them.

Pairs share scenario/trial IDs, not necessarily matched model randomness.
