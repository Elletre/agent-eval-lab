# Model comparison

`baseline` → `improved`

- Paired trials: 70 · fail → pass: 17 · pass → fail: 9 · unchanged: 44
- Pairs dropped because a harness limit stopped one side: 11
- Scenarios that moved: 10 up, 5 down (of 27)
- Change in pass rate: +11% [-6%, +27%], bootstrap over scenarios
- Exact sign test over scenarios: p = 0.302

With 27 scenarios, 6 of them must move the same way before
the sign test can call a difference at 5% — 22% of the suite. Real effects smaller than that exist and this dataset cannot see them.

Pairs share scenario/trial IDs, not necessarily matched model randomness.
