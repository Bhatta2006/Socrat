"""The monthly practice-index refresh reports what changed."""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "content" / "practice_diff.py"
spec = importlib.util.spec_from_file_location("practice_diff", SCRIPT)
assert spec and spec.loader
practice_diff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(practice_diff)


def problem(pid: str, **extra) -> dict:
    return dict(id=pid, title=pid.upper(), platform="Codeforces", rating=1200, **extra)


def test_diff_lists_added_removed_and_changed_fields():
    old = {"a": problem("a"), "b": problem("b"), "c": problem("c")}
    new = {"a": problem("a"), "c": {**problem("c"), "rating": 1400}, "d": problem("d")}
    result = practice_diff.diff(old, new)
    assert result == dict(added=["d"], removed=["b"], changed={"c": ["rating"]})
    text = practice_diff.report(old, new, result, limit=10)
    assert "| Added | 1 |" in text and "`b` B" in text and "rating 1" in text
