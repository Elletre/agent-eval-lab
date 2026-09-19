"""Record source identity without reading credentials or developer-local config."""

import hashlib
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def digest_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def provenance() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL, text=True, timeout=5
            ).strip()
        except (OSError, subprocess.SubprocessError):
            return None

    source = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        source.update(path.name.encode())
        source.update(path.read_bytes())
    lock = ROOT / "uv.lock"
    return {
        "git_revision": git("rev-parse", "HEAD"),
        "working_tree_dirty": bool(git("status", "--porcelain")),
        "source_hash": source.hexdigest(),
        "lock_hash": hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,
        "scorer_version": "1.0.0",
        "environment_version": "1.0.0",
    }
