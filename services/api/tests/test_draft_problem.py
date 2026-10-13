"""Problem drafting pipeline, with a scripted stand-in for the model (no API calls)."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import yaml
from test_validate import BRUTE, GENERATOR, REFERENCE, SMALL

from socrat.catalog.registry import default_catalog
from socrat.catalog.schema import Problem

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "content" / "draft_problem.py"
spec = importlib.util.spec_from_file_location("draft_problem", SCRIPT)
assert spec and spec.loader
drafting = importlib.util.module_from_spec(spec)
spec.loader.exec_module(drafting)


def draft(**overrides):
    fields = dict(
        title="Lantern count total",
        statement="A festival hangs lanterns in rows: row i holds i lanterns. Read n and print how many lanterns rows 0..n hold together.",
        input_format="One integer n.",
        output_format="One integer: the total.",
        constraints=["0 ≤ n ≤ 10^6"],
        examples=[drafting.Example(input="3", output="6"), drafting.Example(input="0", output="0")],
        hints=[
            "What is the smallest case?",
            "Write out n = 4.",
            "Pair the first and last rows.",
            "How many pairs are there?",
        ],
        approach="Pair rows from both ends: n(n+1)/2 in O(1).",
        reference=REFERENCE,
        brute=BRUTE,
        generator=GENERATOR,
        small_generator=SMALL,
        starter_python="n = int(input())\n# TODO\n",
        starter_cpp="#include <iostream>\nint main(){long long n; std::cin>>n; /* TODO */}\n",
        starter_java="public class Main { public static void main(String[] a) { /* TODO */ } }\n",
        time_limit_ms=2000,
    )
    fields.update(overrides)
    return drafting.Draft(**fields)


class FakeModel:
    """Returns queued outputs in order and records each request."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.requests: list[dict] = []
        self.messages = self

    def stream(self, **request):
        self.requests.append(request)
        parsed = self.outputs.pop(0)
        message = SimpleNamespace(
            parsed_output=parsed,
            stop_reason="end_turn",
            content=[{"type": "text", "text": "{}"}],
            usage=SimpleNamespace(input_tokens=1000, output_tokens=2000),
        )
        return _Context(SimpleNamespace(get_final_message=lambda: message))


class _Context:
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return self.stream

    def __exit__(self, *_):
        return None


def solver(code=BRUTE):
    return drafting.Solution(reasoning="sum it", code=code)


def test_a_good_draft_passes_every_gate_and_is_filed_for_review(tmp_path):
    model = FakeModel(draft(), solver())
    raw, gates, usage = drafting.draft_problem(
        model,
        default_catalog(),
        course="zero",
        concept="for-loops",
        difficulty="easy",
        idea="lantern rows",
    )
    statuses = {g.name: g.status for g in gates}
    assert statuses["brute"] == "pass" and statuses["statement"] == "pass"
    assert usage["calls"] == 2 and raw["id"] == "lantern-count-total"
    path = drafting.write_draft(raw, "zero", gates, {"model": "test"}, root=tmp_path)
    Problem.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert "concept tier" in model.requests[0]["messages"][0]["content"]
    assert model.requests[0]["output_format"] is drafting.Draft


def test_failed_gates_are_sent_back_as_feedback(tmp_path):
    wrong = draft(reference="n = int(input())\nprint(n * n)\n")
    model = FakeModel(wrong, draft(), solver())
    _, gates, usage = drafting.draft_problem(
        model,
        default_catalog(),
        course="zero",
        concept="for-loops",
        difficulty="easy",
        idea="lantern rows",
    )
    assert usage["calls"] == 3 and all(g.status != "fail" for g in gates)
    retry = model.requests[1]["messages"][-1]["content"]
    assert "failed these automatic checks" in retry and "examples" in retry


def test_an_ambiguous_statement_is_caught_by_the_independent_solver():
    model = FakeModel(draft(), solver("n = int(input())\nprint(n * (n - 1) // 2)\n"))
    _, gates, _ = drafting.draft_problem(
        model,
        default_catalog(),
        course="zero",
        concept="for-loops",
        difficulty="easy",
        idea="x",
        attempts=1,
    )
    assert {g.name: g.status for g in gates}["statement"] == "fail"
