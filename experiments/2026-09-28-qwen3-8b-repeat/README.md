# The same policy twice: what this suite reports when the answer is known to be nothing

`baseline` was run again on 2026-09-28 with everything held: dataset `fdaa9a69d9c8`, scorer
1.2.0, environment 1.0.0, task 1.0.0, `qwen3:8b` through Ollama 0.17.7 on the same Apple M1
Pro, 27 development scenarios × 3 repeats, 300-second wall clock, one sample at a time,
provider defaults for sampling. No trial was cut short by a limit.

The point of the run is that **there is nothing to find**. Both sides are the same policy, so
every difference below belongs to the instrument.

## Result

| | 2026-09-22 | 2026-09-28 |
| --- | --- | --- |
| Passed trials | 39/81 | 43/81 |
| Pass rate | 48% | 53% |
| Scenarios with mixed repeats | 9/27 | 7/27 |
| Seconds per trial (mean) | 45.9 | 41.6 |

**Change in pass rate: +4.9 points. Eleven of 27 scenarios moved — seven up, four down —
exact sign test p = 0.549.**

| Moved up | Moved down |
| --- | --- |
| `missing_information-01`, `-02`, `-03` | `ambiguous_event-01` |
| `conflicting_memory-02` | `conflicting_memory-03` |
| `constrained_update-02` | `authorized_update-01` |
| `memory_update-03` | `prompt_injection-01` |
| `tool_failure-03` | |

All three `missing_information` scenarios moved the same way, which is what a family-sized
effect looks like — and there was no effect. That is the useful part of the number: a
difference of five points, and a whole family moving together, are both inside what this suite
does on its own.

## What it means for the comparisons in this repository

The published comparison — `baseline` against `improved`, +21 points, p = 0.003, twelve
scenarios moving up and one down — stands, and now stands against a measured background: the
same suite with nothing changed produces five points and eleven moved scenarios. Twenty-one
points and thirteen moved scenarios is a larger, one-directional signal than that, which is
why the sign test reports what it reports.

What the run does undermine is any reading of a *small* difference on this suite. An effect
under roughly five points, or one that rests on a handful of scenarios moving, is not
distinguishable from a rerun of the identical configuration. The
[measurement-faults archive](../archive/2026-09-21-qwen3-8b-measurement-faults) already holds
three ways to get a wrong answer from this harness; this is the fourth, and the only one that
survives a correct harness.

## Provenance

The two runs differ in `source_hash` and `git_revision` and in nothing else that the exporter
records: dataset, prompt, scorer, environment, task, model, eval config, generation config and
the lockfile are identical. The only file changed under `src/` between the two revisions is
`inspect_export.py`, which runs after scoring. `agent-eval compare` refuses the pair for that
reason — it compares only runs from identical source — so the numbers above are computed from
the two exports directly.

## Reproducing

```sh
uv run inspect eval src/agent_eval_lab/inspect_task.py --model ollama/qwen3:8b \
  -T variant=baseline -T split=dev -T time_limit=300 --epochs 3 --max-samples 1 \
  --log-dir logs/repeat
uv run agent-eval export logs/repeat/FILE.eval --output baseline.json
```

Expect different numbers. That is the finding.
