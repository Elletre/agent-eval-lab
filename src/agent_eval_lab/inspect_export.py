"""Normalize complete native Inspect logs without silently dropping failed samples."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from inspect_ai.log import EvalLog, read_eval_log
from pydantic import ValidationError

from agent_eval_lab.schemas import AgentAnswer, ToolCall, World


def _validate_complete(log: EvalLog) -> None:
    if log.status != "success" or log.error or log.invalidated:
        raise ValueError("Only successful, non-invalidated, complete Inspect logs can be exported")
    results = log.results
    if (
        results is None
        or not log.samples
        or results.total_samples != results.completed_samples
        or len(log.samples) != results.total_samples
    ):
        raise ValueError("Incomplete log: all scheduled samples must be present and scored")
    pairs: set[tuple[str, int]] = set()
    for sample in log.samples:
        pair = (str(sample.id), sample.epoch)
        if pair in pairs:
            raise ValueError(f"Duplicate scenario/trial pair: {pair}")
        pairs.add(pair)
        if sample.error or sample.invalidation or not sample.scores:
            raise ValueError(f"Sample {pair} is errored, invalidated, or unscored")
        if "deterministic_checks" not in sample.scores:
            raise ValueError(f"Sample {pair} lacks the deterministic_checks scorer")


def export_log(path: Path) -> dict[str, Any]:
    """Read a native .eval/.json log and return the shared run-artifact schema.

    Explicit Inspect selection (such as --limit) is recorded in eval_config and
    counts as a complete selected run. Interrupted or missing samples are rejected.
    Mock providers remain labelled mock_model, never as model evidence.
    """
    log = read_eval_log(str(path))
    _validate_complete(log)
    metadata = log.eval.metadata or {}
    required = (
        "dataset_hash",
        "prompt_hash",
        "scorer_version",
        "environment_version",
        "variant",
        "split",
        "source_hash",
        "lock_hash",
        "git_revision",
        "working_tree_dirty",
    )
    if any(key not in metadata for key in required):
        raise ValueError("Log lacks required task provenance; regenerate with the current task")
    rows: list[dict[str, Any]] = []
    for sample in log.samples or []:
        assert sample.scores is not None
        score = sample.scores["deterministic_checks"]
        details = score.metadata or {}
        if any(key not in details for key in ("checks", "failures", "family", "trace", "world")):
            raise ValueError(f"Sample {sample.id} has incomplete scorer metadata")
        checks = details["checks"]
        failures = details["failures"]
        if (
            not isinstance(checks, dict)
            or not checks
            or not all(isinstance(k, str) and isinstance(v, bool) for k, v in checks.items())
            or not isinstance(failures, list)
            or not all(isinstance(f, str) for f in failures)
            or score.value not in (0, 1)
            or bool(score.value) != all(checks.values())
            or set(failures) != {key for key, passed in checks.items() if not passed}
            or len(failures) != len(set(failures))
        ):
            raise ValueError(f"Sample {sample.id} has inconsistent score metadata")
        recorded = details["trace"]
        if isinstance(recorded, str):
            # Inspect thins any metadata value over 1k when it writes a sample summary, and a
            # sample restored by `inspect eval-retry` carries the thinned copy: the world
            # snapshots that make a long trace large are gone from the log for good. The
            # verdict and the gates survive, so the trial is real; its trace is not
            # recoverable, and pretending otherwise would put invented tool calls in a
            # published artifact.
            raise ValueError(
                f"Sample {sample.id} lost its trace to log thinning "
                f"({recorded!r}); re-run the sample rather than exporting it"
            )
        trace = [ToolCall.model_validate(item) for item in recorded]
        world = World.model_validate(details["world"])
        if details.get("tool_calls") != len(trace):
            raise ValueError(f"Sample {sample.id} has an inconsistent trace length")
        try:
            answer = AgentAnswer.model_validate_json(sample.output.completion).model_dump(
                mode="json"
            )
        except (ValidationError, ValueError):
            answer = None
        if answer is None and score.value == 1:
            raise ValueError(f"Sample {sample.id} passes despite a malformed final answer")
        # A sample the harness cut short (wall clock, message or token limit) says
        # nothing about the assistant's behaviour. The protocol asks for those to be
        # separated from model behaviour rather than silently counted as failures.
        limit = getattr(sample, "limit", None)
        stopped = None if limit is None else f"{limit.type} limit: {limit.reason}"
        if stopped is not None and bool(score.value):
            raise ValueError(f"Sample {sample.id} passed after hitting a harness limit")
        rows.append(
            {
                "scenario_id": str(sample.id),
                "family": details["family"],
                "trial": sample.epoch,
                "passed": bool(score.value),
                "checks": checks,
                "failures": failures,
                "tool_calls": len(trace),
                "tool_errors": sum(call.result.get("ok") is False for call in trace),
                "answer": answer,
                "trace": [call.model_dump(mode="json") for call in trace],
                "final_world": world.model_dump(mode="json"),
                "usage": {
                    model: usage.model_dump(mode="json")
                    for model, usage in sample.model_usage.items()
                },
                "elapsed_seconds": sample.total_time,
                "error": stopped,
            }
        )
    return {
        "schema_version": 1,
        "kind": "mock_model" if log.eval.model.split("/", 1)[0] == "mockllm" else "model",
        "variant": metadata["variant"],
        "split": metadata["split"],
        "provenance": {
            **{key: metadata[key] for key in required if key not in {"variant", "split"}},
            "model": log.eval.model,
            # Inspect merges provider defaults with task config and CLI overrides.
            # plan.config already contains the latter two in precedence order.
            "generation_config": log.eval.model_generate_config.merge(log.plan.config).model_dump(
                mode="json"
            ),
            "eval_config": log.eval.config.model_dump(mode="json"),
            "task_version": log.eval.task_version,
            "packages": log.eval.packages,
            "revision": log.eval.revision.model_dump(mode="json") if log.eval.revision else None,
            "source_log_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        },
        "results": rows,
    }
