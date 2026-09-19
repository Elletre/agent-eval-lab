"""Small CLI: explicit offline demo, dataset validation, and auditable reports."""

import argparse
import json
from pathlib import Path
from typing import Any

from agent_eval_lab.dataset import load_scenarios
from agent_eval_lab.demo import demo_run
from agent_eval_lab.reporting import compare_runs, report_markdown


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = json.loads(path.read_text())
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate all dataset cases")
    validate.add_argument("--dataset", type=Path)
    demo = commands.add_parser("demo", help="Run oracle fixtures, NOT an LLM evaluation")
    demo.add_argument("--dataset", type=Path)
    demo.add_argument("--split", choices=["dev", "test", "all"], default="dev")
    demo.add_argument("--variant", choices=["control", "faults"], default="control")
    demo.add_argument("--repeats", type=int, default=1)
    demo.add_argument("--output", type=Path, default=Path("runs/demo.json"))
    report = commands.add_parser("report", help="Render a saved run as Markdown")
    report.add_argument("run", type=Path)
    report.add_argument("--output", type=Path, required=True)
    compare = commands.add_parser("compare", help="Compare matching scenario/trial pairs")
    compare.add_argument("left", type=Path)
    compare.add_argument("right", type=Path)
    compare.add_argument("--output", type=Path, required=True)
    export = commands.add_parser("export", help="Export a completed Inspect log")
    export.add_argument("log", type=Path)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            scenarios = load_scenarios(args.dataset, split="all")
            print(f"Validated {len(scenarios)} scenarios.")
        elif args.command == "demo":
            run = demo_run(load_scenarios(args.dataset, args.split), args.variant, args.repeats)
            _write(args.output, json.dumps(run, indent=2, ensure_ascii=False) + "\n")
            _write(args.output.with_suffix(".md"), report_markdown(run))
            print(f"Harness fixtures only (no model): {args.output}")
        elif args.command == "report":
            _write(args.output, report_markdown(_read(args.run)))
        elif args.command == "compare":
            _write(args.output, compare_runs(_read(args.left), _read(args.right)))
        elif args.command == "export":
            from agent_eval_lab.inspect_export import export_log

            _write(args.output, json.dumps(export_log(args.log), indent=2) + "\n")
    except (OSError, ValueError, KeyError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    return 0
