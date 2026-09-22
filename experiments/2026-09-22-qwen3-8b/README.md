# Live run: qwen3 8B, both policies, 27 development scenarios

The first run of this harness whose numbers are about the assistant rather than about the
harness. Read [the archived run](../archive/2026-09-21-qwen3-8b-measurement-faults) first
if you want to see why that distinction needed three attempts.

## Setup

Local `qwen3:8b` served by Ollama 0.17.7 on an Apple M1 Pro, driven through Inspect AI.
27 development scenarios × 3 repeats per policy, one sample at a time. Scorer 1.2.0,
dataset `fdaa9a69d9c8`, commit `1d07eae3`, clean working tree. Per sample: 10 turns, 30
messages, 30,000 tokens, 120 seconds; 1,024 output tokens per response. Provider defaults
for sampling, recorded in the native logs. No test scenarios were run.

## Results

| | `baseline` | `improved` |
| --- | --- | --- |
| Passed trials | 50/79 | 54/72 |
| Pass rate, 95% interval over scenarios | 62% (43%–77%) | 73% (55%–86%) |
| Scenarios passing every repeat | 10/27 | 11/27 |
| Scenarios with mixed repeats | 12/27 | 12/27 |
| Trials with an unauthorized write attempt | 9 | 7 |
| Trials leaving the world in an unexpected state | 8 | 4 |
| Trials with no final answer | 2 | 5 |
| Trials cut short by the 120-second limit | 2 | 9 |
| Tool calls per trial (mean) | 1.4 | 1.4 |

Paired over the 70 comparable trials: 17 fail → pass, 9 pass → fail, 11 pairs dropped
because a limit stopped one side. Ten scenarios moved up, five moved down.

**Change in pass rate: +11 points, 95% interval [−6, +27], exact sign test p = 0.30.**

That is not a result. Six scenarios must move the same way before this dataset can call a
difference at 5%, and the net movement was five. The explicit policy looks better and this
suite cannot show that it is.

## By family

| Family | `baseline` | `improved` |
| --- | ---: | ---: |
| memory_update | 7/9 | 8/8 |
| ambiguous_event | 4/9 | 2/7 |
| tool_failure | 7/9 | 7/8 |
| prompt_injection | 9/9 | 9/9 |
| missing_information | 5/9 | 2/8 |
| authorized_update | 4/9 | 6/8 |
| read_only | 9/9 | 8/8 |
| conflicting_memory | 3/8 | 6/9 |
| constrained_update | 2/8 | 6/7 |

Two to nine trials per cell: these are directions to look, not measurements.

- **Writing improved, asking got worse.** `constrained_update` and `conflicting_memory`
  roughly doubled; `missing_information` and `ambiguous_event` fell. The explicit policy
  tells the model to identify the exact event and the exact values before changing
  anything, which is what the write families reward. Where the right move is to stop and
  ask a specific question, it more often answered anyway or asked without naming what was
  unclear — the failed gate is `expected_status` or `required_fact_alternatives`.
- **Prompt injection is saturated at 9/9 for both.** With the email identifier readable,
  this model reports the requested fact and ignores the instructions inside the message.
  The family as written is too easy for this model and needs harder cases before it can
  discriminate anything.
- **Unauthorized write attempts, the guardrail: 9 against 7.** No movement worth naming.
  The question the project asks — better completion without more unintended action — has
  no answer here in either direction.

## What is still wrong with this run

- **The wall clock interacted with the variable under test.** The longer policy makes this
  model think longer, so it hit the 120-second limit nine times against the baseline's
  two. Those trials are excluded rather than counted as failures, but the exclusion is
  uneven, and the next run should raise the limit (`-T time_limit=300`) before anything
  else.
- **Sampling settings are provider defaults**, so repeats vary for reasons unrelated to
  the policies. Twelve of 27 scenarios gave mixed outcomes across three repeats in both
  variants.
- **One model, one machine, one day.** Nothing here transfers to another model, and
  nothing here is a claim about prompt engineering in general.
- **No semantic review yet.** Literal answer checks passed these trials; whether the
  clarifications were actually useful is a question for the review rubric in
  `docs/evaluation-protocol.md`, not for this table.

## Reproducing

```sh
uv sync --locked --extra providers
uv run inspect eval src/agent_eval_lab/inspect_task.py --model ollama/qwen3:8b \
  -T variant=baseline -T split=dev --epochs 3 --max-samples 1 --log-dir logs/baseline
uv run inspect eval src/agent_eval_lab/inspect_task.py --model ollama/qwen3:8b \
  -T variant=improved -T split=dev --epochs 3 --max-samples 1 --log-dir logs/improved
uv run agent-eval export logs/baseline/FILE.eval --output baseline.json
uv run agent-eval export logs/improved/FILE.eval --output improved.json
uv run agent-eval compare baseline.json improved.json --output comparison.md
```

Expect different numbers: the provider's sampling is not pinned, and a different machine
will hit the wall clock a different number of times.
