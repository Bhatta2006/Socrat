'use client';

import { useEffect, useRef, useState } from 'react';
import CodeWorkspace from './code-workspace';
import TodaySession from './learning-session';

type Block = { mode: string; minutes: number; upsolve_minutes?: number; title: string; timed: boolean; modality?: string; exercise_ids: string[] };
type Plan = { revision: number; review_digest: string; status: string; feasibility: string;
  start_date: string;
  feasible_target_date: string; provisional: boolean; reason_codes: string[]; needs_refresh?: boolean;
  weekly_reserve_minutes: number; assessment_reservation_minutes: number;
  controller: { workload_minutes: number };
    schedule: { minutes: number; weekdays: number[]; target_date: string };
  days: { date: string; status: string; capacity_minutes: number; blocks: Block[]; deferred_reviews: string[] }[];
  nodes: { concept_id: string; state: string; blocked_by: string[] }[] };
const label = (value: string) => value.replaceAll('_', ' ');
const messages: Record<string, string> = {
  completed_diagnostic_required: 'Finish your diagnostic before creating a plan.',
  no_safe_independent_candidate: 'Reviewed practice is not available for your current readiness yet. Your evidence is saved.',
  goal_content_unavailable: 'Your learning content is under review. Your plan and evidence are preserved.',
  feasible_schedule_confirmation_required: 'Choose a feasible target date and review the revised plan.',
  plan_evidence_stale: 'New evidence or a new day changed your plan. Refresh it before confirming.',
  plan_revision_stale: 'Your plan changed in another window. Reload the saved plan.',
  plan_review_stale: 'Reload and review the latest plan before confirming.',
};

export default function Planner({ goalId, csrfToken }: { goalId: string; csrfToken: string }) {
  const [enabled, setEnabled] = useState(false);
  const [sessionsEnabled, setSessionsEnabled] = useState(false);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [minutes, setMinutes] = useState(20);
  const [target, setTarget] = useState('');
  const [weekdays, setWeekdays] = useState<number[]>([0, 2, 4]);
  const key = useRef<{ signature: string; value: string } | null>(null);

  useEffect(() => {
    let active = true;
    fetch('/api/v1/features').then(response => response.json()).then(async features => {
      if (!active || !features.planning) return;
      setEnabled(true);
      setSessionsEnabled(Boolean(features.learning_sessions));
      const response = await fetch(`/api/v1/goals/${goalId}/curriculum`);
      if (response.ok && active) {
        const value = await response.json(); setPlan(value);
        setWeekdays(value.schedule.weekdays);
        setTarget(value.schedule.target_date === 'no_fixed_date' ? '' : value.schedule.target_date);
      } else if (response.status !== 404 && active) setError('Your plan could not be loaded. Please retry.');
    }).catch(() => { if (active) setError('Your plan could not be loaded. Please retry.'); });
    return () => { active = false; };
  }, [goalId]);

  async function act(action: string, changes: Record<string, unknown> = {}) {
    const body = { action, expected_revision: plan?.revision ?? 0,
      ...(action === 'confirm' ? { reviewed_digest: plan?.review_digest } : {}), ...changes };
    const signature = JSON.stringify(body);
    if (key.current?.signature !== signature) key.current = { signature, value: crypto.randomUUID() };
    setPending(true); setError('');
    try {
      const response = await fetch(`/api/v1/goals/${goalId}/curriculum/commands`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        body: JSON.stringify({ ...body, idempotency_key: key.current.value }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(messages[data.error?.code] ?? 'The plan could not be saved. Please retry.');
      setPlan(data); key.current = null;
      setWeekdays(data.schedule.weekdays);
      setTarget(data.schedule.target_date === 'no_fixed_date' ? '' : data.schedule.target_date);
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  if (!enabled) return null;
  return <section className="card card-border mt-6" aria-label="Learning plan" aria-busy={pending}>
    <div className="card-body">
        <h3 className="card-title">Your learning plan</h3>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!plan ? <><p>Build the next two weeks from your saved evidence and available time.</p>
        <button className="btn" disabled={pending} onClick={() => act('generate')}>Create learning plan</button></> : <>
        <TodaySession goalId={goalId} csrfToken={csrfToken} curriculumRevision={plan.revision} />
        <p role="status">{label(plan.status)} · {label(plan.feasibility)} · {plan.controller.workload_minutes} minutes per planned day</p>
        {plan.provisional && <p>Some skills have limited evidence. Future lessons stay locked until their prerequisites are verified.</p>}
        {plan.needs_refresh && <div className="alert">New evidence changed your readiness. Refresh your plan.</div>}
        <p>Estimated feasible target: {plan.feasible_target_date}. Each week reserves {plan.weekly_reserve_minutes} minutes for repair, review, and assessment, including a {plan.assessment_reservation_minutes}-minute assessment block.</p>
        {plan.reason_codes.map(reason => <p key={reason}>{label(reason)}</p>)}
        {plan.days.find(day => day.blocks.length)?.blocks.find(block => block.mode === 'independent') && <p className="font-semibold">Next independent action: {plan.days.find(day => day.blocks.length)!.blocks.find(block => block.mode === 'independent')!.title}. Review and confirm the schedule before starting.</p>}
        <div className="grid gap-3 sm:grid-cols-2">{plan.days.map(day => <article className="card card-border" key={day.date}>
          <div className="card-body p-4"><h4 className="font-semibold">{day.date} · {label(day.status === 'draft' ? plan.status === 'confirmed' ? 'scheduled' : plan.status : day.status)}</h4>
            {day.status === 'content_gap' && <p>Waiting for reviewed practice that fits your readiness and time.</p>}
            {day.blocks.map((block, index) => <p key={index}>{label(block.mode)}: {block.title} · {block.minutes} min{block.timed ? ' · timed' : ''}{block.upsolve_minutes ? ` + ${block.upsolve_minutes} min optional upsolve` : ''}</p>)}
            {!sessionsEnabled && plan.status === 'confirmed' && day.date === plan.start_date && day.blocks.filter(block => block.mode === 'independent' && block.modality === 'code').map(block => <CodeWorkspace key={block.exercise_ids[0]} goalId={goalId} exerciseId={block.exercise_ids[0]} csrfToken={csrfToken} />)}
            {day.deferred_reviews.length > 0 && <p>Reviews deferred within your time limit: {day.deferred_reviews.map(label).join(', ')}.</p>}
          </div></article>)}</div>
        <details><summary>Why this path</summary>{plan.nodes.map(node => <p key={node.concept_id}>{label(node.concept_id)}: {label(node.state)}{node.blocked_by.length ? `; first verify ${node.blocked_by.map(label).join(', ')}` : ''}.</p>)}</details>
        <div className="flex flex-wrap gap-3">
          {plan.status === 'draft' && <button className="btn" disabled={pending || plan.feasibility === 'date_unfeasible' || plan.needs_refresh || !plan.days.some(day => day.blocks.length)} onClick={() => act('confirm')}>Confirm reviewed plan</button>}
          <button className="btn" disabled={pending} onClick={() => act('refresh')}>Refresh plan</button>
          <button className="btn" disabled={pending} onClick={() => act('recover')}>Recalculate after missed days</button>
          {plan.status === 'confirmed' && <button className="btn" disabled={pending} onClick={() => act('pause')}>Pause plan</button>}
          {plan.status === 'paused' && <button className="btn" disabled={pending} onClick={() => act('resume')}>Resume and review</button>}
        </div>
        <label>Lighter day minutes <input className="input w-full" type="number" min={20} max={plan.schedule.minutes - 1} value={minutes} onChange={event => setMinutes(Number(event.target.value))} /></label>
        <button className="btn" disabled={pending || minutes >= plan.schedule.minutes || minutes < 20} onClick={() => act('lighter', { minutes })}>Review lighter plan</button>
        <label>Target date <input className="input w-full" type="date" value={target} onChange={event => setTarget(event.target.value)} /></label>
        <button className="btn" disabled={pending} onClick={() => act('recover', { target_date: target || 'no_fixed_date' })}>Review revised date</button>
        <fieldset><legend>Practice days</legend><div className="flex flex-wrap gap-2">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((day, index) => <button className="btn" type="button" aria-pressed={weekdays.includes(index)} key={day} onClick={() => setWeekdays(weekdays.includes(index) ? weekdays.filter(value => value !== index) : [...weekdays, index])}>{day}</button>)}</div></fieldset>
        <button className="btn" disabled={pending || weekdays.length < 3 || weekdays.length > 6} onClick={() => act('recover', { weekdays })}>Review practice days</button>
        <p>Confirming a plan records your schedule. Start today’s session to work through the selected practice.</p>
      </>}
    </div>
  </section>;
}
