"""Small two-course fixture with a cross-course prerequisite."""

from socrat.catalog.registry import build
from socrat.catalog.schema import Course

LESSON = "A focused explanation of the idea with a worked example. " * 6


def quiz(prefix: str, count: int = 3) -> list[dict]:
    return [
        dict(
            id=f"{prefix}-q{i}",
            prompt=f"Question {i} about {prefix}?",
            options=["right", "wrong", "also wrong"],
            answer=0,
            explanation="Because it is right.",
            difficulty=1 + i % 3,
        )
        for i in range(count)
    ]


def concept(cid: str, module: str, prerequisites=(), problems=(), minutes=40) -> dict:
    return dict(
        id=cid,
        title=cid.replace("-", " ").title(),
        summary=f"Learn {cid} properly.",
        module=module,
        prerequisites=list(prerequisites),
        difficulty=2,
        estimated_minutes=minutes,
        lesson=LESSON,
        key_points=["one", "two"],
        resources=[
            dict(
                title="Official docs",
                url="https://docs.python.org/3/",
                kind="docs",
                source="Python",
                minutes=10,
            ),
            dict(
                title="A video",
                url="https://www.youtube.com/watch?v=abc",
                kind="video",
                source="YT",
                minutes=12,
            ),
        ],
        quiz=quiz(cid),
        problems=list(problems),
    )


def problem(pid: str, concept_id: str, difficulty: str) -> dict:
    return dict(
        id=pid,
        title=pid.title(),
        concepts=[concept_id],
        difficulty=difficulty,
        statement="Read a number and print twice its value, carefully.",
        input_format="One integer n.",
        output_format="The value 2n.",
        examples=[dict(input="2\n", output="4\n")],
        hints=["What operation doubles?", "Multiply by two."],
        approach="Multiply the input by two and print it.",
        reference="print(int(input()) * 2)\n",
        tests=[
            dict(input="2\n", expected="4\n", public=True),
            dict(input="5\n", expected="10\n", public=False),
        ],
    )


def basics() -> Course:
    return Course.model_validate(
        dict(
            id="basics",
            title="Basics",
            tagline="Start from nothing.",
            description="A tiny course used by tests to exercise the engine.",
            version="1.0.0",
            languages=["python", "cpp", "java"],
            levels=[
                dict(id="new", label="New", description="Never coded"),
                dict(id="some", label="Some", description="Wrote code", start_concept="loops"),
            ],
            modules=[
                dict(
                    id="start",
                    title="Start",
                    summary="The first steps.",
                    concepts=["values", "loops"],
                ),
                dict(id="more", title="More", summary="Going further.", concepts=["functions"]),
            ],
            concepts=[
                concept("values", "start", problems=["double"]),
                concept("loops", "start", ["values"], problems=["sum-loop"]),
                concept("functions", "more", ["loops"]),
            ],
            problems=[problem("double", "values", "easy"), problem("sum-loop", "loops", "medium")],
        )
    )


def algo() -> Course:
    return Course.model_validate(
        dict(
            id="algo",
            title="Algorithms",
            tagline="Interview patterns.",
            description="A tiny algorithms course depending on the basics course.",
            version="1.0.0",
            languages=["python", "cpp", "java"],
            levels=[
                dict(id="new", label="New", description="Never coded"),
                dict(id="ok", label="Okay", description="Solved some", start_concept="arrays"),
            ],
            modules=[
                dict(
                    id="core",
                    title="Core",
                    summary="Core ideas.",
                    concepts=["arrays", "two-pointers"],
                ),
                dict(id="graphs", title="Graphs", summary="Graph ideas.", concepts=["bfs"]),
            ],
            concepts=[
                concept("arrays", "core", ["basics:functions"], problems=["arr-easy", "arr-hard"]),
                concept("two-pointers", "core", ["arrays"]),
                concept("bfs", "graphs", ["two-pointers"]),
            ],
            problems=[problem("arr-easy", "arrays", "easy"), problem("arr-hard", "arrays", "hard")],
        )
    )


def catalog():
    return build([basics(), algo()])
