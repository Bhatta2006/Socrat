import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SUPPORTED_LANGUAGES,
  GOAL_TRACKS,
  SESSION_MINUTES,
  evaluateGoal,
  buildDailyPlan,
  classifyEvidence,
  diagnosticTransition,
  recoverPlan,
} from './model.mjs';

const valid = Object.freeze({
  ageConfirmed: true,
  track: 'foundations',
  language: 'python',
  experience: 'none',
  daysPerWeek: 3,
  minutesPerSession: 20,
  targetCoverageStatus: 'released',
});

test('launch scope is exact', () => {
  assert.deepEqual(SUPPORTED_LANGUAGES, ['python', 'cpp', 'java']);
  assert.deepEqual(GOAL_TRACKS, ['foundations', 'interview', 'competitive']);
  assert.deepEqual(SESSION_MINUTES, [20, 30, 45, 60, 90]);
});

test('a complete beginner is accepted into Foundations', () => {
  assert.deepEqual(evaluateGoal(valid), {
    status: 'accepted',
    activePolicy: 'foundations',
    reasonCodes: ['foundations_goal_selected'],
    invalidFields: [],
  });
});

test('low-readiness interview and competitive learners get a Foundations bridge', () => {
  for (const track of ['interview', 'competitive']) {
    const result = evaluateGoal({ ...valid, track, language: 'java', experience: 'syntax_only' });
    assert.equal(result.status, 'accepted_with_bridge');
    assert.equal(result.activePolicy, 'foundations');
    assert.deepEqual(result.reasonCodes, ['foundation_prerequisites_required']);
  }
});

test('unsupported language is waitlisted before commitment checks', () => {
  const result = evaluateGoal({ ...valid, language: 'javascript', daysPerWeek: 1 });
  assert.equal(result.status, 'waitlist');
  assert.deepEqual(result.reasonCodes, ['unsupported_language']);
});

test('unreleased competitive coverage is waitlisted', () => {
  const result = evaluateGoal({ ...valid, track: 'competitive', experience: 'solved_problems', targetCoverageStatus: 'unreleased' });
  assert.equal(result.status, 'waitlist');
  assert.deepEqual(result.reasonCodes, ['competitive_target_not_released']);
});

test('minimum practice commitment is enforced', () => {
  const result = evaluateGoal({ ...valid, daysPerWeek: 2 });
  assert.equal(result.status, 'ineligible');
  assert.deepEqual(result.reasonCodes, ['minimum_practice_commitment_not_met']);
});

test('missing adult confirmation is ineligible', () => {
  const result = evaluateGoal({ ...valid, ageConfirmed: false });
  assert.equal(result.status, 'ineligible');
  assert.deepEqual(result.reasonCodes, ['adult_confirmation_required']);
});

test('malformed inputs require confirmation and never fall through', () => {
  const result = evaluateGoal({ ...valid, track: 'unknown', minutesPerSession: 25 });
  assert.equal(result.status, 'confirmation_required');
  assert.deepEqual(result.reasonCodes, ['input_confirmation_required']);
  assert.deepEqual([...result.invalidFields].sort(), ['minutes_per_session', 'track']);
});

test('every plan exactly fits its selected budget and includes independent work', () => {
  for (const track of GOAL_TRACKS) {
    for (const minutes of SESSION_MINUTES) {
      const plan = buildDailyPlan(track, minutes);
      assert.equal(plan.reduce((sum, block) => sum + block.minutes, 0), minutes);
      assert.equal(plan.some((block) => block.independent), true);
    }
  }
});

test('help levels have exact evidence classifications', () => {
  assert.deepEqual(classifyEvidence(0), { classification: 'independent', masteryMultiplier: 1 });
  assert.deepEqual(classifyEvidence(3), { classification: 'heavily_assisted', masteryMultiplier: 0.35 });
  assert.deepEqual(classifyEvidence(5), { classification: 'learning_only', masteryMultiplier: 0 });
  assert.throws(() => classifyEvidence(6));
});

test('diagnostic transitions expose stable reason codes', () => {
  assert.equal(diagnosticTransition('interview', 'correct').reasonCode, 'clean_reasoning_observed');
  assert.equal(diagnosticTransition('foundations', 'incorrect').reasonCode, 'prerequisite_signal_detected');
  assert.equal(diagnosticTransition('competitive', 'unsure').reasonCode, 'uncertainty_or_no_evidence');
});

test('missed-day recovery adds no backlog and preserves capacity', () => {
  const plan = buildDailyPlan('interview', 45);
  const recovery = recoverPlan(plan, 3);
  assert.equal(recovery.backlogMinutesAdded, 0);
  assert.equal(recovery.plan.reduce((sum, block) => sum + block.minutes, 0), 45);
  assert.equal(recovery.reasonCode, 'capacity_bounded_recovery');
});

test('routing and plan generation are deterministic for equal inputs', () => {
  assert.deepEqual(evaluateGoal(valid), evaluateGoal({ ...valid }));
  assert.deepEqual(buildDailyPlan('competitive', 90), buildDailyPlan('competitive', 90));
});
