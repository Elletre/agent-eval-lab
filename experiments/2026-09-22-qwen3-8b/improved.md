# Model evaluation

Variant: `improved` · Split: `dev`

Synthetic tasks with deterministic gates. Answer checks are literal, not semantic.

| Measure | Result |
|---|---:|
| Unique scenarios | 27 |
| Trials | 81 |
| Passed trials | 54/81 (66.7%) |
| Pass rate, 95% interval over scenarios | 67% (48%–81%) |
| Scenarios passing every repeat | 11 |
| Scenarios with mixed repeat outcomes | 12 |
| Tool calls / errors | 107 / 7 |
| Tool calls per trial (mean / max) | 1.3 / 3 |

Repeated trials are not independent new scenarios, so the interval counts
scenarios (27), not trials (81). A hand-authored
diagnostic suite does not support a population-level claim either way.

## Scenario families

| Family | Passed trials |
|---|---:|
| ambiguous_event | 2/9 |
| authorized_update | 6/9 |
| conflicting_memory | 6/9 |
| constrained_update | 6/9 |
| memory_update | 8/9 |
| missing_information | 2/9 |
| prompt_injection | 9/9 |
| read_only | 8/9 |
| tool_failure | 7/9 |

## Failed gates

- `authorized_write_attempts`: 7
- `exact_final_state`: 7
- `expected_status`: 23
- `forbidden_facts_absent`: 14
- `required_fact_alternatives`: 19
- `required_facts`: 16
- `required_observations`: 10
- `required_tools_used`: 10
- `valid_answer`: 14

## Run identity

- **dataset_hash:** `fdaa9a69d9c8c6a5b5d6f2029df7f3594b7a3a10759d16a78ae164daf5b07d1c`
- **prompt_hash:** `97a1351f3fbae67f0ded893df1f144dac0d809ff5cf331644b2c9610328654d4`
- **scorer_version:** `1.2.0`
- **environment_version:** `1.0.0`
- **source_hash:** `da5cbb1bc7a82dbff2ca5f06ef1a378f5212338e9a8e91563b9d5285022614c1`
- **lock_hash:** `aa55e610702d572ed06a3419cef05a7242f8b34c6122e3fc8aff1fdcdb0ddfd9`
- **git_revision:** `40ecebe26df2829fc645e28d4f488c811b55cf7f`
- **working_tree_dirty:** `False`
- **model:** `ollama/qwen3:8b`
- **generation_config:** `{'max_retries': None, 'timeout': None, 'attempt_timeout': None, 'stream_idle_timeout': None, 'max_connections': None, 'adaptive_connections': None, 'system_message': None, 'max_tokens': 1024, 'top_p': None, 'temperature': None, 'stop_seqs': None, 'best_of': None, 'frequency_penalty': None, 'presence_penalty': None, 'logit_bias': None, 'seed': None, 'top_k': None, 'num_choices': None, 'logprobs': None, 'top_logprobs': None, 'prompt_logprobs': None, 'parallel_tool_calls': False, 'internal_tools': None, 'max_tool_output': None, 'cache_prompt': None, 'fallback_models': None, 'fail_on_refusal': None, 'verbosity': None, 'effort': None, 'reasoning_effort': None, 'reasoning_mode': None, 'reasoning_tokens': None, 'reasoning_summary': None, 'reasoning_history': None, 'response_schema': None, 'extra_headers': None, 'extra_body': None, 'modalities': None, 'cache': None, 'batch': None}`
- **eval_config:** `{'limit': None, 'sample_id': None, 'sample_shuffle': None, 'epochs': 3, 'epochs_reducer': None, 'approval': None, 'review': None, 'notification': None, 'fail_on_error': True, 'continue_on_fail': False, 'retry_on_error': None, 'score_on_error': False, 'message_limit': 30, 'token_limit': 30000, 'token_limit_type': None, 'turn_limit': 10, 'time_limit': 120, 'working_limit': None, 'cost_limit': None, 'max_samples': 1, 'max_dataset_memory': None, 'max_tasks': None, 'max_subprocesses': None, 'max_sandboxes': None, 'sandbox_cleanup': True, 'sandbox_prebuilt': False, 'log_samples': True, 'log_realtime': True, 'log_images': True, 'log_model_api': None, 'log_buffer': None, 'log_shared': 0, 'score_display': True, 'acp_server': None}`
- **task_version:** `1.0.0`
- **packages:** `{'inspect_ai': '0.3.266'}`
- **revision:** `{'type': 'git', 'origin': '', 'commit': '40ecebe', 'dirty': False}`
- **source_log_sha256:** `199c129dea150f80fb5b1e08e7d9d7a5da878a6eb775b90af67605507289b3ed`

Per-trial answers, tool attempts, and world snapshots are in the adjacent JSON run.
