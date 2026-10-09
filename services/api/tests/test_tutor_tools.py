"""Tutor tools: each returns learner-scoped data, and tool calls stream as UI events."""

import asyncio
import json

from test_learner_api import client, login, onboard  # noqa: F401  (client is a fixture)

from socrat.assistant import service as assistant
from socrat.assistant.gateway import Event, ToolSpec, execute, valid_arguments
from socrat.assistant.tools import TOOLS, Toolbox, resolve_concept
from socrat.catalog.registry import default_catalog
from socrat.config import Settings


def toolbox_for(client):  # noqa: F811
    me = client.get("/api/v1/me").json()
    return Toolbox(client.app.state.engine, default_catalog(), me["id"])


def call(box: Toolbox, name: str, **arguments):
    text, failed = asyncio.run(box.run(name, arguments))
    return (text if failed or not text.startswith(("{", "[")) else json.loads(text)), failed


def test_every_tool_answers_for_an_enrolled_learner(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers, course="dsa", level="new-to-programming")
    box = toolbox_for(client)
    progress, failed = call(box, "get_progress")
    assert not failed and progress["concepts"] and progress["practice_level"]
    assert progress["concepts"][0]["lesson"].startswith("[")
    plan, _ = call(box, "get_plan", days=3)
    assert len(plan["days"]) <= 3 and plan["projected_finish"]
    recs, _ = call(box, "recommend_problems", concept="two pointers", count=3)
    assert len(recs["problems"]) == 3
    # Socrat's own judged problems come first, then external ones; all as name-only links.
    assert recs["problems"][0]["platform"] == "Socrat"
    assert all(
        p["link"].startswith("[") and ("](https://" in p["link"] or "](/problems/" in p["link"])
        for p in recs["problems"]
    )
    found, _ = call(box, "search_library", query="two sum", platform="LeetCode")
    assert any("Two Sum" in p["link"] for p in found["problems"])
    topics, _ = call(box, "next_topics")
    assert topics["topics"] and topics["topics"][0]["why"]
    guide, _ = call(box, "get_concept_guide", concept="dsa:binary-search")
    assert guide["key_points"] and "approach" not in json.dumps(guide).lower()
    recent, _ = call(box, "get_recent_work", days=7)
    assert "submissions" in recent
    profile, failed = call(box, "get_codeforces_profile")
    assert not failed and "not linked" in profile
    external = next(p for p in recs["problems"] if p["platform"] != "Socrat")
    saved, _ = call(box, "save_problems", problem_ids=[external["id"], "nope"])
    assert len(saved["saved"]) == 1
    listing = client.get("/api/v1/library?status=bookmarked").json()
    assert listing["items"][0]["id"] == external["id"]
    missing, failed = call(box, "get_concept_guide", concept="underwater basket weaving")
    assert failed and missing.startswith("Error:")


def test_concepts_resolve_by_id_or_name():
    catalog = default_catalog()
    assert resolve_concept(catalog, "dsa:two-pointers") == "dsa:two-pointers"
    assert resolve_concept(catalog, "Two Pointers") == "dsa:two-pointers"
    assert resolve_concept(catalog, "segment tree") == "cp:segment-tree"
    assert resolve_concept(catalog, "zzz") is None


def test_arguments_are_validated_before_running():
    spec = next(t for t in TOOLS if t.name == "recommend_problems")
    assert valid_arguments(spec, {"count": 3, "platform": "CSES"})
    assert not valid_arguments(spec, {"platform": "HackerRank"})
    assert not valid_arguments(spec, {"count": "three"})
    assert not valid_arguments(spec, {"unknown": 1})

    async def boom(name, arguments):
        raise RuntimeError("db down")

    specs = {spec.name: spec}
    assert asyncio.run(execute(specs, boom, "recommend_problems", {}))[1] is True
    assert asyncio.run(execute(specs, boom, "nope", {}))[1] is True
    assert asyncio.run(execute(specs, boom, "recommend_problems", None))[1] is True


class ScriptedProvider:
    """Calls one tool through the real runner, then answers."""

    name = "scripted"

    def __init__(self):
        self.tool_output = ""

    async def converse(self, system, turns, max_tokens, tools=None, run_tool=None, max_rounds=4):
        assert tools and run_tool and "# Tools" in system
        yield Event("text", "<level>5</level>Let me check your plan.")
        yield Event("tool_call", name="get_plan", arguments={"days": 2})
        self.tool_output, _ = await run_tool("get_plan", {"days": 2})
        yield Event("tool_result", name="get_plan", text=self.tool_output)
        yield Event("text", "Tomorrow you have a lesson.")


def test_tool_calls_stream_as_events_and_text_is_joined(client):  # noqa: F811
    headers = login(client)
    onboard(client, headers)
    box = toolbox_for(client)
    settings = Settings(_env_file=None, environment="test")
    plan = assistant.TurnPlan("thread", "general", 5, None, [], "fallback")
    provider = ScriptedProvider()

    async def collect():
        return [
            e async for e in assistant.stream_reply(provider, plan, settings, box.specs, box.run)
        ]

    events = asyncio.run(collect())
    kinds = [kind for kind, _ in events]
    assert kinds[0] == "meta" and "tool" in kinds and kinds[-1] == "done"
    tool = next(data for kind, data in events if kind == "tool")
    assert tool == {"name": "get_plan", "label": "Looking at your plan"}
    done = events[-1][1]
    assert done["text"] == "Let me check your plan.\n\nTomorrow you have a lesson."
    assert json.loads(provider.tool_output)["days"]


def test_tool_specs_are_well_formed():
    names = [t.name for t in TOOLS]
    assert len(names) == len(set(names))
    for tool in TOOLS:
        assert isinstance(tool, ToolSpec) and tool.parameters["type"] == "object"
        assert set(tool.parameters.get("required", [])) <= set(tool.parameters["properties"])
        assert hasattr(Toolbox, f"_{tool.name}")
