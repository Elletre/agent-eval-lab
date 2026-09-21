# Contributing

Use `uv sync --locked`, then run pytest, Ruff, and mypy as described in the README.

For a new scenario, specify the behavior and expected state delta before changing the agent prompt. Use synthetic data only. Keep development and test cases distinct; document any use of test cases during tuning. Add relevant observation constraints and explicit allowed attempts for a write expected to fail.

A case whose expected outcome is a clarification must also grade what the question says: the conflicting values, the candidate events, or the object and its missing field. A request states the goal and the values the user supplies, never the procedure, the error policy or when to ask — those belong to the policy under test.

For a new scoring rule, add both a passing trace and a plausible bypass that should fail. The negative controls in `tests/test_negative_controls.py` must keep passing zero cases; an idle or vague agent that starts passing is a defect in the dataset, not a result. Review whether the new rule rejects a valid alternate solution. Preserve the offline/model result distinction and update scorer/environment versions when changing semantics.

Keep commits focused on reviewable changes. Do not fabricate model results, dates, annotations, or benchmark claims. Store private/provider logs under ignored `logs/` or `runs/`; explicitly select sanitized artifacts for `reports/`.
