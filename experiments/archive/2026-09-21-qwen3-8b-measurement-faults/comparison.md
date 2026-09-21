# Model comparison

`baseline` → `improved`

- Paired trials: 81 · fail → pass: 22 · pass → fail: 10 · unchanged: 49
- Scenarios that moved: 10 up, 5 down (of 27)
- Change in pass rate: +15% [-2%, +33%], bootstrap over scenarios
- Exact sign test over scenarios: p = 0.302

With 27 scenarios, 6 of them must move the same way before
the sign test can call a difference at 5% — 22% of the suite. Real effects smaller than that exist and this dataset cannot see them.

Pairs share scenario/trial IDs, not necessarily matched model randomness.
