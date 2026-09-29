export const SUPPORTED_LANGUAGES = Object.freeze(['python', 'cpp', 'java']);
export const GOAL_TRACKS = Object.freeze(['foundations', 'interview', 'competitive']);
export const SESSION_MINUTES = Object.freeze([20, 30, 45, 60, 90]);

const EXPERIENCE_REQUIRING_BRIDGE = new Set(['none', 'syntax_only']);

export function evaluateGoal(input) {
  const goal = {
    ageConfirmed: Boolean(input.ageConfirmed),
    track: String(input.track || ''),
    language: String(input.language || ''),
    experience: String(input.experience || ''),
    daysPerWeek: Number(input.daysPerWeek),
    minutesPerSession: Number(input.minutesPerSession),
    targetCoverageStatus: String(input.targetCoverageStatus || 'released'),
  };

  const invalidFields = [];
  if (!GOAL_TRACKS.includes(goal.track)) invalidFields.push('track');
  if (!Number.isInteger(goal.daysPerWeek) || goal.daysPerWeek < 1 || goal.daysPerWeek > 7) invalidFields.push('days_per_week');
  if (!SESSION_MINUTES.includes(goal.minutesPerSession)) invalidFields.push('minutes_per_session');
  if (!goal.experience) invalidFields.push('experience');

  if (invalidFields.length) {
    return decision('confirmation_required', null, ['input_confirmation_required'], invalidFields);
  }
  if (!goal.ageConfirmed) {
    return decision('ineligible', null, ['adult_confirmation_required']);
  }
  if (!SUPPORTED_LANGUAGES.includes(goal.language)) {
    return decision('waitlist', null, ['unsupported_language']);
  }
  if (goal.daysPerWeek < 3) {
    return decision('ineligible', null, ['minimum_practice_commitment_not_met']);
  }
  if (goal.track === 'competitive' && goal.targetCoverageStatus !== 'released') {
    return decision('waitlist', null, ['competitive_target_not_released']);
  }
  if (['interview', 'competitive'].includes(goal.track) && EXPERIENCE_REQUIRING_BRIDGE.has(goal.experience)) {
    return decision('accepted_with_bridge', 'foundations', ['foundation_prerequisites_required']);
  }
  return decision('accepted', goal.track, [`${goal.track}_goal_selected`]);
}
function decision(status, activePolicy, reasonCodes, invalidFields = []) {
  return Object.freeze({
    status,
    activePolicy,
    reasonCodes: Object.freeze([...reasonCodes]),
    invalidFields: Object.freeze([...invalidFields]),
  });
}

const PLAN_SHAPES = Object.freeze({
  20: [3, 4, 5, 8],
  30: [4, 6, 8, 12],
  45: [5, 10, 12, 18],
  60: [7, 12, 16, 25],
  90: [10, 18, 24, 38],
});

const PLAN_COPY = Object.freeze({
  foundations: [
    ['retrieval', 'Recall and trace'],
    ['instruction', 'One small idea'],
    ['guided_practice', 'Guided implementation'],
    ['independent_challenge', 'Independent challenge'],
  ],
  interview: [
    ['retrieval', 'Pattern retrieval'],
    ['contrast', 'Contrast two approaches'],
    ['timed_practice', 'Timed interview practice'],
    ['independent_challenge', 'Unseen independent challenge'],
  ],
  competitive: [
    ['retrieval', 'Fast recall drill'],
    ['targeted_drill', 'Weak-topic drill'],
    ['timed_set', 'Timed mixed set'],
    ['independent_upsolve', 'Independent upsolve'],
  ],
});

export function buildDailyPlan(activePolicy, minutesPerSession) {
  const policy = PLAN_COPY[activePolicy];
  const shape = PLAN_SHAPES[minutesPerSession];
  if (!policy || !shape) throw new Error('Unsupported plan input');

  return Object.freeze(policy.map(([type, label], index) => Object.freeze({
    order: index + 1,
    type,
    label,
    minutes: shape[index],
    independent: type.includes('independent'),
  })));
}

export function classifyEvidence(highestHintLevel) {
  const level = Number(highestHintLevel);
  const table = {
    0: ['independent', 1],
    1: ['lightly_assisted', 0.85],
    2: ['assisted', 0.65],
    3: ['heavily_assisted', 0.35],
    4: ['learning_only', 0],
    5: ['learning_only', 0],
  };
  if (!Object.hasOwn(table, level)) throw new Error('Hint level must be an integer from 0 to 5');
  return Object.freeze({ classification: table[level][0], masteryMultiplier: table[level][1] });
}

export function diagnosticTransition(activePolicy, answer) {
  if (!PLAN_COPY[activePolicy]) throw new Error('Unsupported diagnostic policy');
  if (!['correct', 'incorrect', 'unsure'].includes(answer)) throw new Error('Unsupported diagnostic answer');

  if (answer === 'correct') {
    return Object.freeze({ direction: 'increase_evidence_difficulty', reasonCode: 'clean_reasoning_observed' });
  }
  if (answer === 'incorrect') {
    return Object.freeze({ direction: 'probe_prerequisite', reasonCode: 'prerequisite_signal_detected' });
  }
  return Object.freeze({ direction: 'reduce_complexity', reasonCode: 'uncertainty_or_no_evidence' });
}

export function recoverPlan(plan, missedDays) {
  if (!Array.isArray(plan) || !plan.length) throw new Error('Plan is required');
  const days = Number(missedDays);
  if (!Number.isInteger(days) || days < 1) throw new Error('Missed days must be a positive integer');

  const recovered = plan.map((block) => ({ ...block }));
  return Object.freeze({
    missedDays: days,
    backlogMinutesAdded: 0,
    plan: Object.freeze(recovered.map(Object.freeze)),
    reasonCode: 'capacity_bounded_recovery',
  });
}
