# Independent implementation review

This project was reviewed during implementation by separate AI agents covering architecture and reproducibility, dataset methodology, and the Inspect integration. These were bounded reviews of a portfolio evaluation harness, not an external security certification or a human annotation study.

## Findings and regression coverage

Reviewers inspected the actual code and exercised adversarial cases rather than relying only on the planned architecture.

| Finding | Resolution and evidence |
| --- | --- |
| A tool-name-only requirement can accept an irrelevant lookup followed by a lucky correct answer. | Added explicit observation requirements for tool arguments and success/error outcome. `test_wrong_memory_lookup_cannot_ground_a_lucky_guess` verifies the relevant observation is necessary. |
| Inspect rejects unknown tools or malformed arguments before they reach the tool environment. Initially these attempts disappeared from the custom trace and budget, permitting a false pass. | Reconcile model tool attempts with environment traces and retain framework rejections. `test_inspect_rejected_tool_calls_count_toward_budget` covers unknown tools and malformed arguments through the actual Inspect loop. |
| Unknown observation tools and invalid allowed write attempts could produce malformed or impossible grading expectations. | Validate supported tool names, referenced events, and proposed event values when loading scenarios. The dataset-validation regressions in `tests/test_review_regressions.py` cover these cases. |
| Truthy nonboolean gates such as the string `"false"` could be reported as passing. Inconsistent failure lists could hide or mislabel failed gates. | Require boolean check values and an exact, duplicate-free list of failed gate names. `tests/test_reporting_review.py` exercises malformed artifacts. |
| Two runs missing the same provenance field could be treated as comparable because both values were absent. | Require critical run identity before comparison; model runs also require model identity and configuration. The reporting review tests cover missing identity on both sides. |
| Default data loading assumed an editable source checkout. | Include dataset content in the wheel and resolve the packaged fallback; source checkout remains the documented development workflow. |

Additional checks cover deep-copy isolation between sessions and tool observations, atomic rejection of malformed updates, failed unauthorized writes, write-then-undo behavior, complete final-state comparison, malformed final answers, concurrent Inspect samples, and bounded nonterminating agents. A permitted *attempt* does not permit a successful mutation when the expected final state must remain unchanged.

The reviewer independently ran the full test suite successfully during implementation. Use `uv run pytest -q` to obtain the current test count and result; this note deliberately avoids a count that would become stale as tests are added. Native Inspect-loop tests use `mockllm` and require no provider credentials.

## Interpretation limits

- **No live-model conclusion follows from the example reports.** Oracle-driven controls validate the harness and intentionally corrupted controls demonstrate failure detection. Mock-model integration tests validate wiring. Neither measures LLM capability or proves an improved prompt is better.
- **Final-answer checks are narrow.** Status, required strings, forbidden strings, and observed tool behavior are checked independently. Literal matching is not semantic truth checking. A clarification may be unhelpful despite using the correct status, and a negated statement may still contain a required string. Inspect saved answers and traces using the documented human rubric before making qualitative claims.
- **Observed evidence is bounded.** Argument/outcome requirements eliminate specific wrong-tool and wrong-lookup shortcuts; they do not establish a complete causal proof that every answer fact came from the right observation. The model-generated evidence list is not authoritative.
- **The dataset is authored and small.** Its public test split is a workflow convention, with two test cases per family, not a secret or broadly representative benchmark. Once test cases inform prompt changes, disclose that reuse and obtain fresh cases before claiming new held-out performance.
- **Repeats are within-scenario measurements.** More trials do not create more independent scenarios. Reports show exact paired outcomes without asserting statistical significance or matching provider randomness.
- **Safety checks apply to simulated tools.** No real mailbox or calendar is accessed. Persistent injected failures do not model partial commits, transient recovery, identity verification, or production permission enforcement.
- **Live reproducibility has provider limits.** Record the effective generation settings, model identifier, dependency lock, prompt/dataset/source fingerprints, and native log. A provider may still change the implementation behind a model alias; local hashes cannot freeze that service.

The most useful next validation is a small, budgeted live run on the development split, followed by qualitative inspection of failures. Freeze the policy and experiment configuration before running the test split. Keep any resulting report clearly separate from harness verification artifacts.
