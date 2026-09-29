import {
  evaluateGoal,
  buildDailyPlan,
  classifyEvidence,
  diagnosticTransition,
  recoverPlan,
} from './model.mjs';

document.documentElement.dataset.appReady = 'true';

const state = {
  current: 'welcome',
  goal: null,
  route: null,
  plan: null,
  hintLevel: 0,
};

const orderedProgress = ['welcome', 'goal', 'diagnostic', 'plan', 'practice', 'evidence', 'recovery'];
const hints = [
  'What information must you remember after seeing each value?',
  'Consider a structure that answers “have I seen this value?” quickly.',
  'Maintain a set of seen values; check before inserting each value.',
];

function showScreen(name) {
  document.querySelectorAll('[data-screen]').forEach((screen) => {
    const active = screen.dataset.screen === name;
    screen.hidden = !active;
    screen.classList.toggle('active', active);
  });
  state.current = name;
  updateProgress(name === 'route' ? 'goal' : name === 'complete' ? 'recovery' : name);
  document.querySelector('.stage').focus?.();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function updateProgress(current) {
  const currentIndex = orderedProgress.indexOf(current);
  document.querySelectorAll('[data-progress]').forEach((item) => {
    const index = orderedProgress.indexOf(item.dataset.progress);
    item.classList.toggle('done', index < currentIndex);
    if (index === currentIndex) item.setAttribute('aria-current', 'step');
    else item.removeAttribute('aria-current');
  });
}

document.querySelectorAll('[data-action="next"], [data-action="back"]').forEach((button) => {
  button.addEventListener('click', () => showScreen(button.dataset.target));
});

document.querySelectorAll('input[name="track"]').forEach((radio) => {
  radio.addEventListener('change', () => {
    document.querySelector('#coverage-field').hidden = radio.value !== 'competitive';
  });
});

document.querySelector('#goal-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  state.goal = {
    ageConfirmed: form.get('ageConfirmed') === 'on',
    track: form.get('track'),
    language: form.get('language'),
    experience: form.get('experience'),
    daysPerWeek: Number(form.get('daysPerWeek')),
    minutesPerSession: Number(form.get('minutesPerSession')),
    targetCoverageStatus: form.get('targetCoverageStatus'),
  };
  state.route = evaluateGoal(state.goal);
  renderRoute();
  showScreen('route');
});

function renderRoute() {
  const title = document.querySelector('#route-title');
  const copy = document.querySelector('#route-copy');
  const reason = document.querySelector('#route-reason');
  const continueButton = document.querySelector('#continue-diagnostic');
  const route = state.route;

  const views = {
    accepted: ['You’re in the right starting route.', `We’ll use the ${state.goal.track} policy and verify placement with a short diagnostic.`],
    accepted_with_bridge: ['Your goal stays the same. Your first route builds the missing foundation.', 'You are accepted. Socrat would begin with a Foundations bridge, then return to your interview or competitive target after independent readiness evidence.'],
    waitlist: ['This target is not released in V1.', 'We will state the exact coverage gap rather than inventing a curriculum. You can change the language/target or join the waitlist.'],
    ineligible: ['This pilot cannot continue with these inputs.', 'The beta is adults-only and requires at least 20 minutes on three days each week. This is a program constraint, not a judgment of ability.'],
    confirmation_required: ['Some answers need confirmation.', 'The structured goal is incomplete or invalid, so Socrat will not guess.'],
  };

  [title.textContent, copy.textContent] = views[route.status];
  reason.innerHTML = `<strong>Decision reason</strong><br><code>${route.reasonCodes.join(', ')}</code>`;
  continueButton.hidden = !['accepted', 'accepted_with_bridge'].includes(route.status);
}

document.querySelector('#continue-diagnostic').addEventListener('click', () => showScreen('diagnostic'));

document.querySelector('#diagnostic-submit').addEventListener('click', () => {
  const selected = document.querySelector('input[name="diagnostic-answer"]:checked');
  const error = document.querySelector('#diagnostic-error');
  if (!selected) {
    error.textContent = 'Choose the answer that best matches your current reasoning.';
    error.hidden = false;
    return;
  }
  error.hidden = true;
  const transition = diagnosticTransition(state.route.activePolicy, selected.value);
  const explanations = {
    increase_evidence_difficulty: 'Clean reasoning was observed. The next item would become slightly harder to reduce uncertainty efficiently.',
    probe_prerequisite: 'This answer suggests a prerequisite misconception. The next item would isolate that prerequisite before moving forward.',
    reduce_complexity: 'There is not enough evidence yet. The next item would use a simpler trace instead of treating uncertainty as failure.',
  };
  const result = document.querySelector('#diagnostic-result');
  result.innerHTML = `<strong>Adaptive next step</strong><p>${explanations[transition.direction]}</p><code>${transition.reasonCode}</code>`;
  result.hidden = false;
  document.querySelector('#diagnostic-submit').hidden = true;
  document.querySelector('#diagnostic-continue').hidden = false;
});

document.querySelector('#diagnostic-continue').addEventListener('click', () => {
  state.plan = buildDailyPlan(state.route.activePolicy, state.goal.minutesPerSession);
  renderPlan();
  showScreen('plan');
});

function renderPlan() {
  const total = state.plan.reduce((sum, block) => sum + block.minutes, 0);
  document.querySelector('#plan-summary').textContent = `Built for the ${state.route.activePolicy} policy in ${displayLanguage(state.goal.language)}.`;
  document.querySelector('#plan-total').textContent = `${total} minutes`;
  document.querySelector('#plan-list').innerHTML = state.plan.map((block) => `
    <li><span class="number">${block.order}</span><strong>${block.label}</strong><small>${block.minutes} min${block.independent ? ' · independent' : ''}</small></li>
  `).join('');
}

document.querySelector('#hint-button').addEventListener('click', () => {
  state.hintLevel = Math.min(state.hintLevel + 1, hints.length);
  document.querySelector('#hint-level').textContent = String(state.hintLevel);
  document.querySelector('#hint-copy').textContent = hints[state.hintLevel - 1];
  if (state.hintLevel === hints.length) document.querySelector('#hint-button').disabled = true;
});

document.querySelector('#practice-submit').addEventListener('click', () => {
  const approach = document.querySelector('#approach').value.trim();
  const error = document.querySelector('#practice-error');
  if (approach.length < 12) {
    error.textContent = 'Write at least one concrete step before submitting. The prototype does not count a blank click as evidence.';
    error.hidden = false;
    return;
  }
  error.hidden = true;
  renderEvidence(classifyEvidence(state.hintLevel));
  showScreen('evidence');
});

function renderEvidence(evidence) {
  const readable = evidence.classification.replaceAll('_', ' ');
  document.querySelector('#evidence-title').textContent = `This attempt is ${readable}.`;
  document.querySelector('#evidence-copy').textContent = state.hintLevel === 0
    ? 'No hint was used, so the attempt can contribute independent evidence after correctness and operational checks.'
    : `You used help through level ${state.hintLevel}. The work still matters for learning, but Socrat keeps it separate from independent proof.`;
  document.querySelector('#evidence-weight').textContent = `${Math.round(evidence.masteryMultiplier * 100)}% weight`;
  document.querySelector('#evidence-proof').textContent = state.hintLevel === 0 ? 'Independent attempt' : 'Assisted learning';

  const recovery = recoverPlan(state.plan, 3);
  const minutes = recovery.plan.reduce((sum, block) => sum + block.minutes, 0);
  document.querySelector('#recovery-copy').textContent = `Today remains ${minutes} minutes. Reason: ${recovery.reasonCode}.`;
}

document.querySelector('#restart').addEventListener('click', () => window.location.reload());

function displayLanguage(id) {
  return ({ python: 'Python', cpp: 'C++', java: 'Java' })[id] || id;
}

document.documentElement.dataset.handlersReady = 'true';
