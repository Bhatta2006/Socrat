"""Pattern files: schema and cross-references to existing concepts, problems and atoms."""

import copy

import pytest
import yaml
from pydantic import ValidationError

from socrat.catalog import patterns
from socrat.catalog.atoms import load_taxonomy
from socrat.catalog.registry import CONTENT_ROOT, CatalogError, load

ORIGINAL = {"origin": "original", "author": "Socrat Learning"}
VALID = {
    "id": "dsa:sliding-window/variable-size",
    "concept": "dsa:sliding-window",
    "title": "Variable-size window",
    "tracks": ["interview", "competitive"],
    "recognise": [
        "Contiguous subarray or substring",
        "Longest or shortest stretch that stays valid",
        "Validity changes monotonically as the window grows",
    ],
    "state": "window [left, right] plus whatever makes it valid",
    "transition": "grow right; shrink left while invalid",
    "complexity": {"time": "O(n)", "space": "O(k)"},
    "variants": [
        {"id": "longest-unique-substring", "band": 2, "problem": "longest-unique-substring"},
        {
            "id": "longest-repeating-replacement",
            "band": 4,
            "problem": "leetcode:longest-repeating-character-replacement",
        },
    ],
    "pitfalls": ["sliding-window-repair"],
    "problems": {
        "native": ["longest-unique-substring"],
        "external": ["leetcode:longest-repeating-character-replacement"],
    },
    "provenance": ORIGINAL,
}


@pytest.fixture(scope="module")
def catalog():
    return load()


@pytest.fixture(scope="module")
def external_ids():
    return patterns.external_problem_ids(CONTENT_ROOT.parent / "practice" / "problems.jsonl")


def write(root, payload, name=None):
    course, rest = payload["id"].split(":", 1)
    concept, slug = rest.split("/")
    folder = root / course / concept
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{name or slug}.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


def load_one(tmp_path, catalog, external_ids, payload, name=None):
    write(tmp_path, payload, name)
    taxonomy = load_taxonomy(CONTENT_ROOT.parent / "atoms")
    return patterns.load(tmp_path, catalog, taxonomy, lambda: external_ids)


def test_valid_pattern_loads_with_safe_defaults(tmp_path, catalog, external_ids):
    loaded = load_one(tmp_path, catalog, external_ids, VALID)
    pattern = loaded["dsa:sliding-window/variable-size"]
    assert pattern.status == "provisional"
    assert pattern.provenance.review is None


def test_missing_directory_means_no_patterns(tmp_path, catalog):
    assert patterns.load(tmp_path / "absent", catalog, set(), lambda: set()) == {}


def test_repository_patterns_are_provisional_original_and_unreviewed(catalog):
    assert catalog.patterns  # the M5 pilot packs
    for pattern in catalog.patterns.values():
        assert pattern.status == "provisional" and pattern.provenance.review is None
        assert pattern.provenance.origin == "original"
        assert pattern.id in catalog.pattern_atoms
        pack = catalog.pattern_atoms[pattern.id]
        assert pack.status == "draft" and pack.review is None


@pytest.mark.parametrize(
    "change, message",
    [
        (
            {"id": "dsa:dynamic-everything/variable-size", "concept": "dsa:dynamic-everything"},
            "unknown concept",
        ),
        ({"problems": {"native": ["no-such-problem"], "external": []}}, "unknown native problem"),
        (
            {"problems": {"native": [], "external": ["leetcode:no-such-slug"]}},
            "unknown external problem",
        ),
        ({"pitfalls": ["made-up-misconception"]}, "unknown misconception"),
        ({"atoms": ["no-such-atom"]}, "unknown atom"),
    ],
)
def test_broken_references_fail_validation(tmp_path, catalog, external_ids, change, message):
    payload = {**copy.deepcopy(VALID), **change}
    with pytest.raises(CatalogError, match=message):
        load_one(tmp_path, catalog, external_ids, payload)


def test_variant_must_point_at_a_listed_problem(tmp_path, catalog, external_ids):
    payload = copy.deepcopy(VALID)
    payload["variants"][0]["problem"] = "kth-largest-stream"
    with pytest.raises(CatalogError, match="variant longest-unique-substring.*not listed"):
        load_one(tmp_path, catalog, external_ids, payload)


def test_file_name_and_folder_must_match_the_id(tmp_path, catalog, external_ids):
    with pytest.raises(CatalogError, match="file path must match"):
        load_one(tmp_path, catalog, external_ids, VALID, name="other-name")


def test_concept_prefix_must_match_the_concept():
    payload = {**copy.deepcopy(VALID), "concept": "dsa:binary-search"}
    with pytest.raises(ValidationError, match="must start with its concept"):
        patterns.Pattern.model_validate(payload)


def test_recognition_cues_are_three_and_short():
    with pytest.raises(ValidationError):
        patterns.Pattern.model_validate({**VALID, "recognise": VALID["recognise"][:2]})
    long_cues = ["word " * 25] * 3
    with pytest.raises(ValidationError, match="60 words"):
        patterns.Pattern.model_validate({**VALID, "recognise": long_cues})


def test_variant_ladder_runs_easy_to_hard():
    payload = copy.deepcopy(VALID)
    payload["variants"] = list(reversed(payload["variants"]))
    with pytest.raises(ValidationError, match="easy to hard"):
        patterns.Pattern.model_validate(payload)


def test_templates_are_bounded_per_language():
    payload = {**copy.deepcopy(VALID), "template": {"python": "x = 1\n" * 26}}
    with pytest.raises(ValidationError, match="25 lines"):
        patterns.Pattern.model_validate(payload)


def test_new_content_must_declare_provenance_and_cannot_claim_calibration_unreviewed():
    payload = {k: v for k, v in copy.deepcopy(VALID).items() if k != "provenance"}
    with pytest.raises(ValidationError):
        patterns.Pattern.model_validate(payload)
    with pytest.raises(ValidationError, match="human review"):
        patterns.Pattern.model_validate({**copy.deepcopy(VALID), "status": "calibrated"})
