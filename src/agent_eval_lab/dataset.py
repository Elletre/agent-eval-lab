"""Dataset loading: fail fast rather than silently dropping malformed scenarios."""

import hashlib
import json
from pathlib import Path

from pydantic import TypeAdapter

from agent_eval_lab.schemas import Scenario

DEFAULT_DATASET = Path(__file__).resolve().parents[2] / "data" / "scenarios.json"


def load_scenarios(path: Path | None = None, split: str = "dev") -> list[Scenario]:
    if split not in {"dev", "test", "all"}:
        raise ValueError("split must be dev, test, or all")
    source = path or DEFAULT_DATASET
    scenarios = TypeAdapter(list[Scenario]).validate_python(json.loads(source.read_text()))
    if len({item.id for item in scenarios}) != len(scenarios):
        raise ValueError("Dataset contains duplicate scenario IDs")
    selected = [item for item in scenarios if split == "all" or item.split == split]
    if not selected:
        raise ValueError(f"No scenarios in split {split}")
    return selected


def dataset_hash(scenarios: list[Scenario]) -> str:
    payload = json.dumps(
        [s.model_dump() for s in scenarios], sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(payload).hexdigest()
