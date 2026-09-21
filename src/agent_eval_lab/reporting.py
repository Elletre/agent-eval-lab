"""Honest summaries with strict pairing and no pseudoreplication claims."""

from collections import Counter, defaultdict
from typing import Any


def validate_run(run: dict[str, Any]) -> None:
    if run.get("schema_version") != 1 or run.get("kind") not in {
        "scripted_fixture",
        "model",
        "mock_model",
    }:
        raise ValueError("Unsupported run schema or kind")
    if not isinstance(run.get("results"), list) or not run["results"]:
        raise ValueError("Run has no results")
    identity = run.get("provenance")
    if not isinstance(identity, dict):
        raise ValueError("Missing run provenance")
    for field in ("dataset_hash", "source_hash", "scorer_version", "environment_version"):
        if not isinstance(identity.get(field), str) or not identity[field]:
            raise ValueError(f"Missing critical provenance: {field}")
    if run["kind"] in {"model", "mock_model"}:
        for field in ("model", "prompt_hash", "generation_config", "eval_config", "packages"):
            if field not in identity or identity[field] is None:
                raise ValueError(f"Missing model provenance: {field}")
        if not isinstance(identity["model"], str) or not identity["model"]:
            raise ValueError("Missing model identity")
        if (identity["model"].split("/", 1)[0] == "mockllm") != (run["kind"] == "mock_model"):
            raise ValueError("Mock provider and run kind disagree")
    if not isinstance(run.get("variant"), str) or run.get("split") not in {"dev", "test", "all"}:
        raise ValueError("Invalid run variant or split")
    keys = []
    families: dict[str, str] = {}
    for row in run["results"]:
        if not isinstance(row, dict) or not isinstance(row.get("scenario_id"), str):
            raise ValueError("Invalid result row")
        if type(row.get("trial")) is not int or row["trial"] < 1:
            raise ValueError("trial must be a positive integer")
        keys.append((row["scenario_id"], row["trial"]))
        if not isinstance(row.get("family"), str) or not row["family"]:
            raise ValueError("Missing scenario family")
        if families.setdefault(row["scenario_id"], row["family"]) != row["family"]:
            raise ValueError("Scenario family differs between repeats")
        if type(row.get("passed")) is not bool:
            raise ValueError("passed must be a boolean")
        checks = row.get("checks")
        if (
            not isinstance(checks, dict)
            or not checks
            or any(
                not isinstance(key, str) or type(value) is not bool for key, value in checks.items()
            )
        ):
            raise ValueError("checks must map gate names to booleans")
        if row["passed"] != all(checks.values()):
            raise ValueError("Outcome disagrees with check gates")
        expected_failures = [key for key, value in checks.items() if not value]
        failures = row.get("failures")
        if not isinstance(failures, list) or any(not isinstance(f, str) for f in failures):
            raise ValueError("Invalid failure list")
        if len(failures) != len(set(failures)) or set(failures) != set(expected_failures):
            raise ValueError("Failure list disagrees with check gates")
        for field in ("tool_calls", "tool_errors"):
            if type(row.get(field)) is not int or row[field] < 0:
                raise ValueError(f"Invalid {field}")
        if row["tool_errors"] > row["tool_calls"]:
            raise ValueError("Tool errors exceed tool attempts")
        if row.get("error") and row["passed"]:
            raise ValueError("Errored trial cannot pass")
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate scenario/trial rows")


def summarize(run: dict[str, Any]) -> dict[str, Any]:
    validate_run(run)
    rows = run["results"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario_id"]].append(row)
    families: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        families[row["family"]].append(row["passed"])
    return {
        "scenarios": len(grouped),
        "trials": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "pass_rate": sum(row["passed"] for row in rows) / len(rows),
        "stable_pass_scenarios": sum(
            all(row["passed"] for row in group) for group in grouped.values()
        ),
        "mixed_outcome_scenarios": sum(
            len({row["passed"] for row in group}) > 1 for group in grouped.values()
        ),
        "repeat_counts": sorted({len(group) for group in grouped.values()}),
        "families": {
            name: {"passed": sum(values), "trials": len(values)}
            for name, values in sorted(families.items())
        },
        "failures": dict(Counter(failure for row in rows for failure in row["failures"])),
        "tool_calls": sum(row["tool_calls"] for row in rows),
        "tool_errors": sum(row["tool_errors"] for row in rows),
        "mean_tool_calls": sum(row["tool_calls"] for row in rows) / len(rows),
        "max_tool_calls": max(row["tool_calls"] for row in rows),
    }


def report_markdown(run: dict[str, Any]) -> str:
    stats = summarize(run)
    model_run = run["kind"] == "model"
    heading = "Model evaluation" if model_run else "Harness verification (NOT model performance)"
    text = [
        f"# {heading}",
        "",
        f"Variant: `{run['variant']}` · Split: `{run['split']}`",
        "",
        "Synthetic tasks with deterministic gates. Answer checks are literal, not semantic.",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Unique scenarios | {stats['scenarios']} |",
        f"| Trials | {stats['trials']} |",
        f"| Passed trials | {stats['passed']}/{stats['trials']} ({stats['pass_rate']:.1%}) |",
        f"| Scenarios passing every repeat | {stats['stable_pass_scenarios']} |",
        f"| Scenarios with mixed repeat outcomes | {stats['mixed_outcome_scenarios']} |",
        f"| Tool calls / errors | {stats['tool_calls']} / {stats['tool_errors']} |",
        f"| Tool calls per trial (mean / max) | {stats['mean_tool_calls']:.1f} / "
        f"{stats['max_tool_calls']} |",
        "",
        "Repeated trials are not independent new scenarios. No population-level claim or",
        "statistical significance is inferred from this small, hand-authored dataset.",
        "",
    ]
    if not model_run:
        text += [
            "This run uses scripted or mock controls. Control traces may read the oracle.",
            "Pass rates validate the evaluator only. They do not compare LLM capability.",
            "",
        ]
    text += ["## Scenario families", "", "| Family | Passed trials |", "|---|---:|"]
    for family, value in stats["families"].items():
        text.append(f"| {family} | {value['passed']}/{value['trials']} |")
    text += ["", "## Failed gates", ""]
    text += [f"- `{name}`: {count}" for name, count in sorted(stats["failures"].items())] or [
        "None."
    ]
    text += ["", "## Run identity", ""]
    for key, value in run["provenance"].items():
        text.append(f"- **{key}:** `{value}`")
    text += [
        "",
        "Per-trial answers, tool attempts, and world snapshots are in the adjacent JSON run.",
        "",
    ]
    return "\n".join(text)


def compare_runs(left: dict[str, Any], right: dict[str, Any]) -> str:
    validate_run(left)
    validate_run(right)
    if left["kind"] != right["kind"] or left["split"] != right["split"]:
        raise ValueError("Run kind and split must match")
    fields = [
        "dataset_hash",
        "scorer_version",
        "environment_version",
        "source_hash",
        "lock_hash",
        "model",
        "generation_config",
        "eval_config",
        "packages",
    ]
    for key in fields:
        if left["provenance"].get(key) != right["provenance"].get(key):
            raise ValueError(f"Incomparable runs: {key} differs")

    def keyed(run: dict[str, Any]) -> dict[tuple[str, int], dict[str, Any]]:
        return {(row["scenario_id"], row["trial"]): row for row in run["results"]}

    a, b = keyed(left), keyed(right)
    if a.keys() != b.keys():
        raise ValueError("Runs must have the same scenario/trial pairs")
    improved = sum(not a[key]["passed"] and b[key]["passed"] for key in a)
    regressed = sum(a[key]["passed"] and not b[key]["passed"] for key in a)
    label = (
        "Model comparison" if left["kind"] == "model" else "Harness comparison (NOT LLM results)"
    )
    return "\n".join(
        [
            f"# {label}",
            "",
            f"`{left['variant']}` → `{right['variant']}`",
            "",
            f"- Paired trials: {len(a)}",
            f"- Fail → pass: {improved}",
            f"- Pass → fail: {regressed}",
            f"- Unchanged: {len(a) - improved - regressed}",
            "",
            "Pairs share scenario/trial IDs, not necessarily matched model randomness.",
            "Repeats are not independent scenarios. No significance claim is made.",
            "",
        ]
    )
