"""Simulated learners against the engine (M3 task 15).

Property tests drive whole sessions for random abilities and seeds; the accuracy test fixes
seeds and asserts on the mean across many learners, never on one run.
"""

import statistics

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from socrat.quiz import simulate
from socrat.quiz.config import DEFAULT, TRACKS
from socrat.quiz.selection import answered

BANK = simulate.synthetic_bank(per_band=12)
TWO = simulate.synthetic_bank(patterns=("sim:a", "sim:b"), per_band=8)
BY_KEY = {i.key: i for i in BANK + TWO}

abilities = st.floats(min_value=700, max_value=1900)
seeds = st.text(alphabet="abcdef0123456789", min_size=1, max_size=8)
tracks = st.sampled_from(TRACKS)


def session(theta, track, seed, mode="concept_check", max_items=25, bank=BANK, **kw):
    learner = simulate.Learner(true_theta=theta)
    return simulate.run(bank, learner, track, mode, seed, max_items=max_items, **kw)


@settings(max_examples=60, deadline=None)
@given(abilities, tracks, seeds)
def test_ladder_guarantees_hold(theta, track, seed):
    steps = session(theta, track, seed)
    for n in range(1, len(steps)):
        before, now = steps[:n], steps[n]
        used = {s.item for s in before}
        bands_left = {i.band for i in BANK if i.pool == "practice" and i.key not in used}
        last = before[-1]
        assert abs(now.band - last.band) <= DEFAULT.max_jump
        if last.outcome == "wrong":
            assert now.band <= last.band  # a wrong answer never raises difficulty
        tail = [s for s in before if s.band == last.band][-2:]
        streak = before[-2:] == tail and len(tail) == 2 and all(s.independent for s in tail)
        if streak and last.band < 7 and last.band + 1 in bands_left:
            assert now.band >= last.band + 1


@settings(max_examples=60, deadline=None)
@given(abilities, tracks, seeds)
def test_no_item_is_served_twice_across_sessions(theta, track, seed):
    learner = simulate.Learner(true_theta=theta)
    keys = []
    for n in range(3):
        steps = simulate.run(BANK, learner, track, "concept_check", f"{seed}:{n}")
        keys += [s.item for s in steps]
    assert len(keys) == len(set(keys))


@settings(max_examples=40, deadline=None)
@given(abilities, tracks, seeds, st.sampled_from(["concept_check", "review", "contest"]))
def test_practice_modes_never_serve_assessment_items(theta, track, seed, mode):
    steps = session(theta, track, seed, mode=mode, max_items=None, bank=TWO)
    assert steps
    assert all(BY_KEY[s.item].pool == "practice" for s in steps)


@settings(max_examples=40, deadline=None)
@given(abilities, tracks, seeds)
def test_over_exposed_items_wait_while_others_remain(theta, track, seed):
    practice = [i for i in BANK if i.pool == "practice"]
    hot = {i.key: 0.5 for i in practice[::2]}
    steps = session(theta, track, seed, max_items=10, exposure=hot)
    for n, step in enumerate(steps):
        if step.item not in hot:
            continue
        # Served over the cap only when no fresh item is left at the band chosen.
        used = {s.item for s in steps[:n]}
        fresh = [i for i in practice if i.key not in hot and i.key not in used]
        assert not [i for i in fresh if i.band == step.band]


@settings(max_examples=40, deadline=None)
@given(abilities, seeds)
def test_review_interleaves_patterns(theta, seed):
    steps = session(theta, "interview", seed, mode="review", max_items=None, bank=TWO)
    assert all(a.pattern != b.pattern for a, b in zip(steps, steps[1:], strict=False))


@settings(max_examples=40, deadline=None)
@given(abilities, tracks, seeds)
def test_concept_check_stops_between_six_and_ten(theta, track, seed):
    learner = simulate.Learner(true_theta=theta)
    steps = simulate.run(BANK, learner, track, "concept_check", seed)
    assert 6 <= len(steps) <= 10


@pytest.mark.parametrize("track", TRACKS)
def test_success_rate_tracks_the_target_after_eight_items(track):
    """Mean success on items 9–30 is within ±0.07 of the track target.

    Learners start from a prior within ±100 of their true ability, as placement or prior
    mastery provides. From a far-off prior θ converges slowly (see the M3 report).
    """
    bank = simulate.synthetic_bank(per_band=40)
    target = DEFAULT.target[track]
    rates = []
    for start in (1150, 1300, 1450):
        for n in range(120):
            truth = start - 100 + 200 * ((n * 0.618) % 1)
            learner = simulate.Learner(true_theta=truth, thetas={"sim:window": start})
            steps = simulate.run(
                bank, learner, track, "concept_check", f"{track}{start}{n}", max_items=30
            )
            rates += [s.outcome == "correct" for s in answered(steps)[8:]]
    mean = statistics.mean(rates)
    assert abs(mean - target) <= 0.07, (track, mean)
