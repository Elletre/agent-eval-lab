"""Honest summaries with strict pairing and no pseudoreplication claims."""

from collections import Counter, defaultdict
from typing import Any

from agent_eval_lab.statistics import (
    minimum_detectable_flips,
    paired_delta,
    pass_rate,
    sign_test_exact,
)


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
    recorded = run["results"]
    rows = [row for row in recorded if not row.get("error")]
    if not rows:
        raise ValueError("Every trial was cut short by the harness; there is nothing to summarise")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["scenario_id"]].append(row)
    families: dict[str, list[bool]] = defaultdict(list)
    for row in rows:
        families[row["family"]].append(row["passed"])
    outcomes = {name: [row["passed"] for row in group] for name, group in grouped.items()}
    interval = pass_rate(outcomes)
    return {
        "scenarios": len(grouped),
        "trials": len(rows),
        "stopped_by_limits": len(recorded) - len(rows),
        "passed": sum(row["passed"] for row in rows),
        "pass_rate": sum(row["passed"] for row in rows) / len(rows),
        "scenario_pass_rate": vars(interval),
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
    rate = stats["scenario_pass_rate"]
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
        "| Pass rate, 95% interval over scenarios | "
        f"{rate['estimate']:.0%} ({rate['low']:.0%}–{rate['high']:.0%}) |",
        f"| Scenarios passing every repeat | {stats['stable_pass_scenarios']} |",
        f"| Scenarios with mixed repeat outcomes | {stats['mixed_outcome_scenarios']} |",
        f"| Tool calls / errors | {stats['tool_calls']} / {stats['tool_errors']} |",
        f"| Tool calls per trial (mean / max) | {stats['mean_tool_calls']:.1f} / "
        f"{stats['max_tool_calls']} |",
        f"| Trials cut short by a harness limit (excluded above) | {stats['stopped_by_limits']} |",
        "",
        "Repeated trials are not independent new scenarios, so the interval counts",
        f"scenarios ({stats['scenarios']}), not trials ({stats['trials']}). A hand-authored",
        "diagnostic suite does not support a population-level claim either way.",
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
    # A pair is only comparable when both sides actually ran: a trial the harness
    # cut short carries no evidence about the assistant on either side.
    dropped = [pair for pair in a if a[pair].get("error") or b[pair].get("error")]
    for pair in dropped:
        del a[pair]
        del b[pair]
    if not a:
        raise ValueError("No comparable pairs remain after removing trials the harness cut short")
    improved = sum(not a[key]["passed"] and b[key]["passed"] for key in a)
    regressed = sum(a[key]["passed"] and not b[key]["passed"] for key in a)

    def outcomes(rows: dict[tuple[str, int], dict[str, Any]]) -> dict[str, list[bool]]:
        grouped: dict[str, list[bool]] = defaultdict(list)
        for (scenario, _), row in rows.items():
            grouped[scenario].append(row["passed"])
        return dict(grouped)

    before, after = outcomes(a), outcomes(b)
    rates_before = {name: sum(v) / len(v) for name, v in before.items()}
    rates_after = {name: sum(v) / len(v) for name, v in after.items()}
    scenarios_up = sum(rates_after[name] > rates_before[name] for name in rates_before)
    scenarios_down = sum(rates_after[name] < rates_before[name] for name in rates_before)
    delta = paired_delta(before, after)
    p_value = sign_test_exact(scenarios_up, scenarios_down)
    needed = minimum_detectable_flips()
    label = (
        "Model comparison" if left["kind"] == "model" else "Harness comparison (NOT LLM results)"
    )
    return "\n".join(
        [
            f"# {label}",
            "",
            f"`{left['variant']}` → `{right['variant']}`",
            "",
            f"- Paired trials: {len(a)} · fail → pass: {improved} · pass → fail: {regressed} · "
            f"unchanged: {len(a) - improved - regressed}",
            f"- Pairs dropped because a harness limit stopped one side: {len(dropped)}",
            f"- Scenarios that moved: {scenarios_up} up, {scenarios_down} down "
            f"(of {len(rates_before)})",
            f"- Change in pass rate: {delta.estimate:+.0%} "
            f"[{delta.low:+.0%}, {delta.high:+.0%}], bootstrap over scenarios",
            "- Exact sign test over scenarios: "
            + ("p < 0.001" if p_value < 0.001 else f"p = {p_value:.3f}"),
            "",
            f"With {len(rates_before)} scenarios, {needed} of them must move the same way before",
            f"the sign test can call a difference at 5% — {needed / len(rates_before):.0%} of the"
            " suite. Real effects smaller than that exist and this dataset cannot see them.",
            "",
            "Pairs share scenario/trial IDs, not necessarily matched model randomness.",
            "",
        ]
    )
