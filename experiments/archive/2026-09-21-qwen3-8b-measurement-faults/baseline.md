# Model evaluation

Variant: `baseline` · Split: `dev`

Synthetic tasks with deterministic gates. Answer checks are literal, not semantic.

| Measure | Result |
|---|---:|
| Unique scenarios | 27 |
| Trials | 81 |
| Passed trials | 16/81 (19.8%) |
| Pass rate, 95% interval over scenarios | 20% (9%–38%) |
| Scenarios passing every repeat | 2 |
| Scenarios with mixed repeat outcomes | 6 |
| Tool calls / errors | 101 / 7 |
| Tool calls per trial (mean / max) | 1.2 / 3 |

Repeated trials are not independent new scenarios, so the interval counts
scenarios (27), not trials (81). A hand-authored
diagnostic suite does not support a population-level claim either way.

## Scenario families

| Family | Passed trials |
|---|---:|
| ambiguous_event | 3/9 |
| authorized_update | 0/9 |
| conflicting_memory | 1/9 |
| constrained_update | 0/9 |
| memory_update | 2/9 |
| missing_information | 2/9 |
| prompt_injection | 0/9 |
| read_only | 3/9 |
| tool_failure | 5/9 |

## Failed gates

- `authorized_write_attempts`: 11
- `exact_final_state`: 9
- `expected_status`: 55
- `forbidden_facts_absent`: 14
- `required_fact_alternatives`: 23
- `required_facts`: 33
- `required_observations`: 23
- `required_tools_used`: 22
- `valid_answer`: 14

## Run identity

- **dataset_hash:** `225849d195d01a05bf52ba8371652994c1e389996cc40bce34f230e43935e584`
- **prompt_hash:** `c5b356738aa53b539c63438a61bda63f0b5a827e4e529d33b0498bb07fb0d400`
- **scorer_version:** `1.1.0`
- **environment_version:** `1.0.0`
- **source_hash:** `3bd802a9434e375a9541e19c130473989e37a180f1dad7452cc0220d47fbb311`
- **lock_hash:** `aa55e610702d572ed06a3419cef05a7242f8b34c6122e3fc8aff1fdcdb0ddfd9`
- **git_revision:** `c4468756c15a32151025491adea92de6ffea5061`
- **working_tree_dirty:** `False`
- **model:** `ollama/qwen3:8b`
- **generation_config:** `{'max_retries': None, 'timeout': None, 'attempt_timeout': None, 'stream_idle_timeout': None, 'max_connections': None, 'adaptive_connections': None, 'system_message': None, 'max_tokens': 1024, 'top_p': None, 'temperature': None, 'stop_seqs': None, 'best_of': None, 'frequency_penalty': None, 'presence_penalty': None, 'logit_bias': None, 'seed': None, 'top_k': None, 'num_choices': None, 'logprobs': None, 'top_logprobs': None, 'prompt_logprobs': None, 'parallel_tool_calls': False, 'internal_tools': None, 'max_tool_output': None, 'cache_prompt': None, 'fallback_models': None, 'fail_on_refusal': None, 'verbosity': None, 'effort': None, 'reasoning_effort': None, 'reasoning_mode': None, 'reasoning_tokens': None, 'reasoning_summary': None, 'reasoning_history': None, 'response_schema': None, 'extra_headers': None, 'extra_body': None, 'modalities': None, 'cache': None, 'batch': None}`
- **eval_config:** `{'limit': None, 'sample_id': None, 'sample_shuffle': None, 'epochs': 3, 'epochs_reducer': None, 'approval': None, 'review': None, 'notification': None, 'fail_on_error': True, 'continue_on_fail': False, 'retry_on_error': None, 'score_on_error': False, 'message_limit': 30, 'token_limit': 30000, 'token_limit_type': None, 'turn_limit': 10, 'time_limit': 120, 'working_limit': None, 'cost_limit': None, 'max_samples': 1, 'max_dataset_memory': None, 'max_tasks': None, 'max_subprocesses': None, 'max_sandboxes': None, 'sandbox_cleanup': True, 'sandbox_prebuilt': False, 'log_samples': True, 'log_realtime': True, 'log_images': True, 'log_model_api': None, 'log_buffer': None, 'log_shared': 0, 'score_display': True, 'acp_server': None}`
- **task_version:** `1.0.0`
- **packages:** `{'inspect_ai': '0.3.266'}`
- **revision:** `{'type': 'git', 'origin': '', 'commit': 'c446875', 'dirty': False}`
- **source_log_sha256:** `11ef5540b33ec476f6658e67f331c29c93297b9b2c18623679bc1c9a6e983e46`

Per-trial answers, tool attempts, and world snapshots are in the adjacent JSON run.
