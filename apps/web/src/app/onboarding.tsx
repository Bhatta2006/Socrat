'use client';

import { FormEvent, useEffect, useState } from 'react';
import DiagnosticFlow from './diagnostic';

const outcomes = {
  foundations: ['programming_readiness', 'foundational_dsa', 'interview_entry_readiness'],
  interview: ['screen_readiness', 'interview_loop_readiness', 'topic_repair'],
  competitive: ['rating_band', 'division_readiness', 'topic_repair', 'contest_consistency'],
};
type Track = keyof typeof outcomes;
type Goal = {
  goal_template_id: Track; language: string; target_outcome: string; target_date: string;
  days_per_week: number; minutes_per_session: number; timezone: string;
  language_experience: string; dsa_experience: string; role_level: string | null;
  platform_or_format: string | null; target_value: string | null;
};
type Review = {
  id?: string; goal: Goal; normalized_statement: string; routing_outcome: string;
  reason_codes: string[]; warnings: string[]; active_track: string | null;
  first_diagnostic_stage: string | null; review_digest: string;
};
const label = (value: string) => value.replaceAll('_', ' ');
const reasons: Record<string, string> = {
  adult_confirmation_required: 'Save your profile with confirmation that you are 18 or older.',
  unsupported_language: 'This language is not available yet.',
  minimum_practice_commitment_not_met: 'Choose at least 3 days a week and 20 minutes per session.',
  competitive_target_not_released: 'Content for this contest target is not available yet.',
  goal_coverage_not_released: 'Content for this goal and language is not available yet.',
  foundations_bridge_not_released: 'The introductory content needed for this goal is not available yet.',
  foundation_prerequisites_required: 'Start with programming foundations while keeping your chosen goal.',
};

export default function Onboarding({ csrfToken, timezone, adultConfirmed, diagnosticsEnabled }: {
  csrfToken: string; timezone: string; adultConfirmed: boolean; diagnosticsEnabled: boolean;
}) {
  const [track, setTrack] = useState<Track>('foundations');
  const [language, setLanguage] = useState('python');
  const [outcome, setOutcome] = useState(outcomes.foundations[0]);
  const [date, setDate] = useState('');
  const [noDate, setNoDate] = useState(false);
  const [days, setDays] = useState(4);
  const [minutes, setMinutes] = useState(30);
  const [experience, setExperience] = useState('none');
  const [dsa, setDsa] = useState('never');
  const [role, setRole] = useState('new_grad');
  const [platform, setPlatform] = useState('codeforces');
  const [target, setTarget] = useState('');
  const [review, setReview] = useState<Review | null>(null);
  const [confirmed, setConfirmed] = useState<Review | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [key, setKey] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    fetch('/api/v1/onboarding/goals', { credentials: 'same-origin' })
      .then(async response => {
        if (!response.ok) throw new Error('Could not load your saved goals.');
        const data = await response.json();
        if (active) setConfirmed(data.items[0] ?? null);
      }).catch(() => { if (active) setError('Could not load your saved goals. Please reload.'); });
    return () => { active = false; };
  }, []);

  async function request(path: string, body: unknown): Promise<Review> {
    const response = await fetch(`/api/v1/onboarding/${path}`, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      const code = (await response.json()).error?.code;
      throw new Error(code === 'goal_review_stale'
        ? 'Availability or your profile changed. Review your goal again.'
        : 'Your goal could not be saved. Review the fields and try again.');
    }
    return response.json();
  }

  async function preview(event: FormEvent) {
    event.preventDefault(); setPending(true); setError('');
    const goal: Goal = {
      goal_template_id: track, language, target_outcome: outcome,
      target_date: noDate ? 'no_fixed_date' : date, timezone,
      days_per_week: days, minutes_per_session: minutes,
      language_experience: experience, dsa_experience: dsa,
      role_level: track === 'interview' ? role : null,
      platform_or_format: track === 'competitive' ? platform : null,
      target_value: track === 'competitive' ? target : null,
    };
    try {
      setReview(await request('preview', goal)); setReviewed(false); setKey(crypto.randomUUID());
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function confirm() {
    if (!review) return;
    setPending(true); setError('');
    try {
      const value = await request('confirm', { goal: review.goal, review_digest: review.review_digest,
        reviewed, idempotency_key: key });
      setConfirmed(value); setReview(null);
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  function select(name: string, value: string, choices: string[], change: (value: string) => void) {
    return <label className="fieldset"><span className="fieldset-legend">{name}</span>
      <select className="select w-full" aria-label={name} value={value} onChange={event => change(event.target.value)}>
        {choices.map(choice => <option key={choice} value={choice}>{label(choice)}</option>)}
      </select></label>;
  }

  return <section className="border-t border-base-300 pt-6" aria-busy={pending}>
    <h2 className="text-2xl font-bold">Your learning goal</h2>
    <p className="mt-2 text-sm">Choose what you want to learn, then review your starting route. Beginners are welcome.</p>
    {!adultConfirmed && <div className="alert mt-4">Save your profile confirming you are 18 or older before continuing.</div>}
    {confirmed && <div className="alert mt-4" data-testid="saved-goal">
      <div><p className="font-semibold">Goal saved{confirmed.routing_outcome === 'waitlist' ? ' on the waitlist' : ''}.</p>
        <p>{confirmed.normalized_statement}</p></div>
    </div>}
    {confirmed?.id && confirmed.routing_outcome.startsWith('accept_') &&
      <DiagnosticFlow key={confirmed.id} goalId={confirmed.id} csrfToken={csrfToken} enabled={diagnosticsEnabled} />}
    {error && <div className="alert alert-error mt-4" role="alert">{error}</div>}
    {review ? <div className="card mt-4 border border-base-300"><div className="card-body">
      <h3 className="card-title">Review your goal</h3>
      <p>{review.normalized_statement}</p>
      <p>Language experience: {label(review.goal.language_experience)}. DSA experience: {label(review.goal.dsa_experience)}.</p>
      <p className="font-semibold">{review.routing_outcome === 'waitlist' ? 'Waitlist' : label(review.routing_outcome)}</p>
      {review.reason_codes.map(reason => <p key={reason}>{reasons[reason] ?? 'Your chosen goal is supported.'}</p>)}
      {review.active_track && <p>Starting route: {label(review.active_track)}. First check: {label(review.first_diagnostic_stage ?? '')}.</p>}
      {review.warnings.length > 0 && <div className="alert alert-warning">This date may be too soon. Consider a later date, a smaller goal, or more practice time.</div>}
      <p className="text-sm">Progress requires independent work and later checks. Job, interview and rating results are never guaranteed.</p>
      <label className="label justify-start gap-3"><input type="checkbox" className="checkbox" checked={reviewed}
        onChange={event => setReviewed(event.target.checked)} />I reviewed this goal and starting route.</label>
      <div className="card-actions"><button type="button" className="btn btn-neutral" onClick={confirm}
        disabled={pending || !reviewed || review.routing_outcome === 'ineligible'}>Confirm goal</button>
        <button type="button" className="btn" disabled={pending} onClick={() => setReview(null)}>Edit goal</button></div>
    </div></div> : <form onSubmit={preview} className="mt-4 space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        {select('Goal', track, Object.keys(outcomes), value => {
          const next = value as Track; setTrack(next); setOutcome(outcomes[next][0]);
        })}
        {select('Programming language', language, ['python', 'cpp', 'java'], setLanguage)}
        {select('Target outcome', outcome, outcomes[track], setOutcome)}
        {track === 'interview' && select('Role level', role, ['intern', 'new_grad', 'early_career', 'experienced_hire'], setRole)}
        {track === 'competitive' && <>
          {select('Contest platform', platform, ['codeforces', 'atcoder', 'codechef', 'other'], setPlatform)}
          <label className="fieldset"><span className="fieldset-legend">Target value</span>
            <input className="input w-full" aria-label="Target value" value={target} required maxLength={200}
              placeholder="Band, division, topics or consistency target" onChange={event => setTarget(event.target.value)} /></label>
        </>}
        {select('Days each week', String(days), ['3', '4', '5', '6', '7'], value => setDays(Number(value)))}
        {select('Minutes per session', String(minutes), ['20', '30', '45', '60', '90'], value => setMinutes(Number(value)))}
        {select('Programming experience', experience, ['none', 'syntax_only', 'solved_problems', 'professional'], setExperience)}
        {select('DSA experience', dsa, ['never', 'studied', 'inconsistent_practice', 'comfortable'], setDsa)}
      </div>
      <label className="label justify-start gap-3"><input className="checkbox" type="checkbox" checked={noDate}
        onChange={event => setNoDate(event.target.checked)} />I have no fixed target date.</label>
      {!noDate && <label className="fieldset"><span className="fieldset-legend">Target date</span>
        <input className="input w-full" type="date" aria-label="Target date" value={date} required onChange={event => setDate(event.target.value)} /></label>}
      <p className="text-sm">Schedule timezone: {timezone}. Change it in your profile if needed.</p>
      <button type="submit" className="btn btn-neutral" disabled={pending || !adultConfirmed}>Review goal</button>
    </form>}
  </section>;
}
