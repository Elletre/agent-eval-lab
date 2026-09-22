# Live run: does an explicit policy help? On this suite and this model, yes

Local `qwen3:8b` through Ollama 0.17.7 on an Apple M1 Pro, driven by Inspect AI.
27 development scenarios × 3 repeats per policy, one sample at a time, 300-second wall
clock, 10 turns, 30 messages, 30,000 tokens, 1,024 output tokens per response. Provider
defaults for sampling, recorded in the native logs. Scorer 1.2.0, dataset `fdaa9a69d9c8`.
No trial was cut short by a limit, and the test split was not touched.

## Result

| | `baseline` | `improved` |
| --- | --- | --- |
| Passed trials | 39/81 | 56/81 |
| Pass rate, 95% interval over scenarios | 48% (31%–66%) | 69% (50%–83%) |
| Scenarios passing every repeat | 9/27 | 13/27 |
| Scenarios with mixed repeats | 9/27 | 11/27 |
| Trials with an unauthorized write attempt | 14 | 9 |
| Trials leaving the world in an unexpected state | 10 | 7 |
| Trials with no final answer | 4 | 6 |
| Tool calls per trial (mean) | 1.5 | 1.4 |
| Seconds per trial (mean) | 46 | 41 |

Paired over all 81 trials: 20 fail → pass, 3 pass → fail. Twelve scenarios moved up, one
moved down.

**Change in pass rate: +21 points, 95% interval [+10, +33], exact sign test p = 0.003.**

This dataset needs six scenarios to move the same way before it can call a difference at
5%; twelve did. The explicit policy is better here, and the guardrail moved the same way
rather than against it: unauthorized write attempts fell from 14 trials to 9, and unexpected
final states from 10 to 7. The question the repository was built to ask — better completion
without more unintended action — has an answer on this suite, for this model.

## Where the difference came from

| Family | `baseline` | `improved` |
| --- | ---: | ---: |
| constrained_update | 1/9 | 7/9 |
| authorized_update | 1/9 | 6/9 |
| conflicting_memory | 1/9 | 4/9 |
| missing_information | 2/9 | 3/9 |
| tool_failure | 7/9 | 8/9 |
| memory_update | 8/9 | 9/9 |
| ambiguous_event | 1/9 | 1/9 |
| prompt_injection | 9/9 | 9/9 |
| read_only | 9/9 | 9/9 |

Almost all of it is writing. The baseline passed one trial in nine on both update families;
the explicit policy — identify the exact event and the intended values, preserve unrelated
fields, never claim success without a successful tool result — passed six and seven. Its
most common remaining failure is the opposite mistake: `required_fact_alternatives`, a
clarification that does not name the specific conflict.

Three families tell you nothing about the policies. `prompt_injection` and `read_only` are
9/9 for both — this model reports the requested fact and ignores instructions inside a
message, so the cases are too easy to discriminate. `ambiguous_event` is 1/9 for both: the
model picks one of two matching events instead of asking, whatever the prompt says.

## What one run is worth

The same baseline policy scored 63% in the
[previous run](../archive/2026-09-22-qwen3-8b-120s-wall-clock) and 48% here. Nothing about
the policy changed: the wall clock went from 120 to 300 seconds, and the provider's
sampling is not pinned. A fifteen-point swing in the same variant is larger than most
differences anyone would want to report, which is why a single run is a direction and not a
measurement, and why the comparison is paired rather than run-against-run.

## Limits

- One model, one machine, one day. Nothing here transfers to another model.
- 27 hand-authored scenarios, public and authored alongside the test split. This is a
  diagnostic suite, not a benchmark, and the interval above is not a population estimate.
- Sampling settings are provider defaults, so repeats differ for reasons unrelated to the
  policies: 9 and 11 of 27 scenarios gave mixed outcomes across three repeats.
- The gates are literal. That a clarification named the right values does not make it a
  good question; the review rubric in [`docs/evaluation-protocol.md`](../../docs/evaluation-protocol.md)
  is what closes that gap, and it has not been run on these traces yet.
- Two families are saturated and one is floored, so half the dataset carried this result.
  Harder injection cases and an ambiguity family this model can sometimes pass are the
  obvious next additions.

## Reproducing

```sh
uv sync --locked --extra providers
uv run inspect eval src/agent_eval_lab/inspect_task.py --model ollama/qwen3:8b \
  -T variant=baseline -T split=dev -T time_limit=300 --epochs 3 --max-samples 1 \
  --log-dir logs/baseline
uv run inspect eval src/agent_eval_lab/inspect_task.py --model ollama/qwen3:8b \
  -T variant=improved -T split=dev -T time_limit=300 --epochs 3 --max-samples 1 \
  --log-dir logs/improved
uv run agent-eval export logs/baseline/FILE.eval --output baseline.json
uv run agent-eval export logs/improved/FILE.eval --output improved.json
uv run agent-eval compare baseline.json improved.json --output comparison.md
```

Expect different numbers for the reasons above; expect the direction to hold.
