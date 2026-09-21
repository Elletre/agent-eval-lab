# Harness verification (NOT model performance)

Variant: `control` · Split: `all`

Synthetic tasks with deterministic gates. Answer checks are literal, not semantic.

| Measure | Result |
|---|---:|
| Unique scenarios | 45 |
| Trials | 45 |
| Passed trials | 45/45 (100.0%) |
| Pass rate, 95% interval over scenarios | 100% (92%–100%) |
| Scenarios passing every repeat | 45 |
| Scenarios with mixed repeat outcomes | 0 |
| Tool calls / errors | 49 / 6 |
| Tool calls per trial (mean / max) | 1.1 / 2 |

Repeated trials are not independent new scenarios, so the interval counts
scenarios (45), not trials (45). A hand-authored
diagnostic suite does not support a population-level claim either way.

This run uses scripted or mock controls. Control traces may read the oracle.
Pass rates validate the evaluator only. They do not compare LLM capability.

## Scenario families

| Family | Passed trials |
|---|---:|
| ambiguous_event | 5/5 |
| authorized_update | 5/5 |
| conflicting_memory | 5/5 |
| constrained_update | 5/5 |
| memory_update | 5/5 |
| missing_information | 5/5 |
| prompt_injection | 5/5 |
| read_only | 5/5 |
| tool_failure | 5/5 |

## Failed gates

None.

## Run identity

- **git_revision:** `2547a726cc78b50299cad4746a3e16c9706afb77`
- **working_tree_dirty:** `True`
- **source_hash:** `3bd802a9434e375a9541e19c130473989e37a180f1dad7452cc0220d47fbb311`
- **lock_hash:** `aa55e610702d572ed06a3419cef05a7242f8b34c6122e3fc8aff1fdcdb0ddfd9`
- **scorer_version:** `1.1.0`
- **environment_version:** `1.0.0`
- **dataset_hash:** `dfd19428c7bad965f5d7a174fbdc7a77da87833a4c040b490a4751d085710b08`
- **model:** `None`
- **generation_config:** `{}`

Per-trial answers, tool attempts, and world snapshots are in the adjacent JSON run.
