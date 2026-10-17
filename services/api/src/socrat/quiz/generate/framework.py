"""Generated quiz items (content.md §8.6).

A family's ``generator.template`` names a trusted authoring module,
``content/quiz/generators/<template>.py``, with one function::

    def generate(rng: random.Random, params: dict) -> Draft

The framework seeds ``rng`` from the family id and seed, so one seed is one item, forever.
The expected answer never comes from the generator: it is the family's ``reference``
expression evaluated on ``draft.values``, and the verifier then requires the shown code to
produce it in every language. A generated item reaches learners only when the committed
manifest (``content/quiz/verified.json``) lists it with the current source digest.
"""

import builtins
import contextlib
import hashlib
import importlib.util
import io
import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from socrat.catalog.quizbank import GeneratorSpec, ItemFormat, Pool, QuizFamily
from socrat.catalog.schema import Language, Model, Slug

BLANK = "___"
FRAMEWORK_VERSION = "2"
MANIFEST = "verified.json"
SAFE_BUILTINS = {
    name: getattr(builtins, name)
    for name in (
        "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "int", "len",
        "list", "map", "max", "min", "pow", "range", "reversed", "round", "set", "sorted",
        "str", "sum", "tuple", "zip",
    )
}  # fmt: skip


class Option(Model):
    text: str = Field(min_length=1, max_length=300)
    misconception: Slug | None = None
    # fill_blank: the code that fills the blank; bug_spot: the whole snippet after the fix.
    fill: dict[Language, str] = Field(default_factory=dict)
    variant: dict[Language, str] = Field(default_factory=dict)


class Draft(Model):
    prompt: str = Field(min_length=5, max_length=2000)
    code: dict[Language, str] = Field(min_length=1)
    options: list[Option] = Field(min_length=2, max_length=6)
    answer: int = Field(ge=0)
    explanation: str = Field(min_length=5, max_length=2000)
    band: int = Field(ge=1, le=7)
    format: ItemFormat | None = None  # overrides the family's format for this item
    values: dict[str, Any] = Field(default_factory=dict)  # inputs of the reference expression
    trace_line: int | None = Field(default=None, ge=1)  # trace items: compare this line only

    @model_validator(mode="after")
    def contract(self):
        if self.answer >= len(self.options):
            raise ValueError("answer index out of range")
        texts = [o.text for o in self.options]
        if len(set(texts)) != len(texts):
            raise ValueError("duplicate options")
        if self.options[self.answer].misconception is not None:
            raise ValueError("the correct option has no misconception")
        for i, option in enumerate(self.options):
            if i != self.answer and option.misconception is None:
                raise ValueError(f"distractor {option.text!r} needs a misconception")
        return self

    def option_text(self, index: int, language: str) -> str:
        option = self.options[index]
        return option.fill.get(cast(Language, language)) or option.text

    def face(self) -> str:
        """What the learner sees, ignoring option order (shuffled at display anyway)."""
        seen = dict(
            prompt=self.prompt, code=self.code, options=sorted(o.text for o in self.options)
        )
        return hashlib.sha256(json.dumps(seen, sort_keys=True).encode()).hexdigest()

    def digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self.model_dump(mode="json"), sort_keys=True).encode()
        ).hexdigest()


Check = Literal["equals", "differs", "none"]


def shown_check(fmt: str) -> Check:
    """What the shown code must print: the answer, anything else (it is buggy), or not run."""
    if fmt in {"output_prediction", "trace"}:
        return "equals"
    if fmt == "bug_spot":
        return "differs"
    return "none"


# ---------------------------------------------------------------- generator modules


def generator_path(root: Path, spec: GeneratorSpec) -> Path:
    return root / "generators" / f"{spec.template}.py"


@lru_cache(maxsize=64)
def _module(path: str, digest: str):
    spec = importlib.util.spec_from_file_location(f"socrat_quiz_gen_{digest[:12]}", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load generator {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not callable(getattr(module, "generate", None)):
        raise ValueError(f"{path}: generator must define generate(rng, params)")
    return module


def module(root: Path, spec: GeneratorSpec):
    path = generator_path(root, spec)
    return _module(str(path), hashlib.sha256(path.read_bytes()).hexdigest())


def rng_for(family: QuizFamily, seed: int) -> random.Random:
    return random.Random(f"{family.id}:{seed}")


def draft(root: Path, family: QuizFamily, seed: int) -> Draft:
    """The item for one seed. Raises ValueError when the generator breaks its contract."""
    if family.generator is None:
        raise ValueError(f"{family.id} has no generator")
    made = module(root, family.generator).generate(rng_for(family, seed), family.generator.params)
    result = made if isinstance(made, Draft) else Draft.model_validate(made)
    missing = set(family.languages) - set(result.code)
    if missing:
        raise ValueError(f"seed {seed}: no code for {sorted(missing)}")
    return result


def expected(family: QuizFamily, item: Draft, root: Path | None = None) -> str:
    """The answer, from the family's reference expression only."""
    assert family.generator is not None
    # Values go in globals: comprehensions in the expression cannot see eval's locals.
    # A generator may export brute-force helpers (HELPERS) for long references.
    helpers = getattr(module(root, family.generator), "HELPERS", {}) if root else {}
    scope = {**helpers, **item.values, "__builtins__": SAFE_BUILTINS}
    value = eval(family.generator.reference, scope)  # noqa: S307 - trusted authoring expression
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def seeds(family: QuizFamily) -> list[tuple[int, Pool]]:
    if family.generator is None:
        return []
    return sorted(
        (seed, pool)
        for pool, span in family.generator.seeds.items()
        for seed in range(span.start, span.stop)
    )


def item_key(family: QuizFamily, seed: int) -> str:
    return f"{family.id}:s{seed}"


def source_digest(root: Path, family: QuizFamily) -> str:
    """Everything that decides a family's generated items."""
    assert family.generator is not None
    parts = [
        FRAMEWORK_VERSION,
        json.dumps(family.model_dump(mode="json"), sort_keys=True),
        generator_path(root, family.generator).read_text(encoding="utf-8"),
    ]
    defects = root / "defects.yaml"
    if defects.exists():
        parts.append(defects.read_text(encoding="utf-8"))
    return hashlib.sha256("\x00".join(parts).encode()).hexdigest()


def run_python(code: str) -> str:
    """Run trusted generator-side Python in process; generators use it to pick inputs."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(code, {"__builtins__": builtins})  # noqa: S102 - trusted authoring code
    return out.getvalue().rstrip()


def fill(code: dict, option: Option) -> dict[str, str]:
    """The snippet in every language with the option's code in the blank."""
    return {str(lang): text.replace(BLANK, option.fill[lang]) for lang, text in code.items()}


# ---------------------------------------------------------------- manifest


def load_manifest(root: Path) -> dict:
    path = root / MANIFEST
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def verified_drafts(
    root: Path, family: QuizFamily, manifest: dict
) -> list[tuple[int, Pool, Draft]]:
    """Generated items a learner may see: listed in the manifest for this exact source."""
    entry = manifest.get(family.id)
    if not entry or entry.get("source") != source_digest(root, family):
        return []
    listed = entry.get("items", {})
    found = []
    for seed, pool in seeds(family):
        digest = listed.get(str(seed))
        if digest is None:
            continue
        item = draft(root, family, seed)
        if item.digest() == digest:
            found.append((seed, pool, item))
    return found
