# Harness verification (NOT model performance)

Variant: `faults` · Split: `all`

Synthetic tasks with deterministic gates. Answer checks are literal, not semantic.

| Measure | Result |
|---|---:|
| Unique scenarios | 40 |
| Trials | 40 |
| Passed trials | 0/40 (0.0%) |
| Scenarios passing every repeat | 0 |
| Scenarios with mixed repeat outcomes | 0 |
| Tool calls / errors | 76 / 7 |

Repeated trials are not independent new scenarios. No population-level claim or
statistical significance is inferred from this small, hand-authored dataset.

This run uses scripted or mock controls. Control traces may read the oracle.
Pass rates validate the evaluator only. They do not compare LLM capability.

## Scenario families

| Family | Passed trials |
|---|---:|
| ambiguous_event | 0/5 |
| authorized_update | 0/5 |
| conflicting_memory | 0/5 |
| memory_update | 0/5 |
| missing_information | 0/5 |
| prompt_injection | 0/5 |
| read_only | 0/5 |
| tool_failure | 0/5 |

## Failed gates

- `authorized_write_attempts`: 34
- `exact_final_state`: 37
- `expected_status`: 1
- `forbidden_facts_absent`: 1
- `required_facts`: 1
- `tool_budget`: 5
- `valid_answer`: 1

## Run identity

- **git_revision:** `3f2bce1afec3c121656674c28a5a4f7c000fc245`
- **working_tree_dirty:** `False`
- **source_hash:** `a5485008e56f9d2a675feb772a77c32556ae1fc3d6f7aae240655494e5168c45`
- **lock_hash:** `75f099d39b03feecfcac21a5685db2232f213d29c14ce14839a735d5362829c7`
- **scorer_version:** `1.0.0`
- **environment_version:** `1.0.0`
- **dataset_hash:** `131372404dab572dd11dacc3719a44e1bcbabcf7d9341fdaaae7268dc03e290c`
- **model:** `None`
- **generation_config:** `{}`

Per-trial answers, tool attempts, and world snapshots are in the adjacent JSON run.
