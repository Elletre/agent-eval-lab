# Contributing

Use `uv sync --locked`, then run pytest, Ruff, and mypy as described in the README.

For a new scenario, specify the behavior and expected state delta before changing the agent prompt. Use synthetic data only. Keep development and test cases distinct; document any use of test cases during tuning. Add relevant observation constraints and explicit allowed attempts for a write expected to fail.

For a new scoring rule, add both a passing trace and a plausible bypass that should fail. Review whether the new rule rejects a valid alternate solution. Preserve the offline/model result distinction and update scorer/environment versions when changing semantics.

Keep commits focused on reviewable changes. Do not fabricate model results, dates, annotations, or benchmark claims. Store private/provider logs under ignored `logs/` or `runs/`; explicitly select sanitized artifacts for `reports/`.
