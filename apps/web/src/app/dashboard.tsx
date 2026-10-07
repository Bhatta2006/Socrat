'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import DiagnosticFlow from './diagnostic';
import Planner from './planner';
import AssessmentFlow from './assessment';
import TodaySession from './learning-session';

type Progress = {
  goal_id: string | null; statement?: string; track?: string; language?: string; target_date?: string;
  timezone?: string; local_date?: string; uncertainty?: string; missed_days?: number;
  today: { action: string; minutes?: number; session_id?: string | null };
  plan?: { revision: number; status: string; feasibility: string; milestones: { concept_id?: string; date?: string; [key: string]: unknown }[] } | null;
  concepts?: { id: string; title: string; band: string; confidence: number; retention_due: boolean; estimate: number | null; reason_codes: string[] }[];
  schedule?: { date: string; status: string; minutes: number }[];
  trend?: { start: string; end: string; independent: { count: number; solve_rate: number | null }; assisted: { count: number; solve_rate: number | null } }[];
  evidence?: { id: string; concept_ids: string[]; score: number; mode: string; hint_level: number; occurred_at: number; reason_code: string }[];
  assessments?: { id: string; kind: string; status: string; result: { score?: number; evidence_current?: boolean } | null }[];
  mastery_changes?: { concept: string; before: string; after: string; reason: string }[];
  assessment_due?: { kind: string; cycle: string; can_defer: boolean; deferred_until: number | null; actionable: boolean } | null;
};
const label = (value: string) => value.replaceAll('_', ' ');
const actions: Record<string, string> = {
  choose_goal: 'Choose your learning goal', waitlist: 'Your goal is on the waitlist', diagnostic: 'Take your diagnostic',
  generate_plan: 'Create your learning plan', confirm_plan: 'Review and confirm your plan', refresh_plan: 'Refresh your plan',
  recover: 'Choose a comfortable recovery plan', resume_plan: 'Resume your plan',
  start_session: 'Start today’s session', resume_session: 'Resume today’s session', assessment: 'Take your independent assessment',
  today_complete: 'Today’s session is complete', rest: 'A planned rest day', program_complete: 'Review your program evidence',
  content_unavailable: 'Content is under review. Your work is saved.', review_pending: 'Your diagnostic is awaiting review.',
  learning_unavailable: 'Learning is temporarily unavailable. Your work is saved.',
  assessment_review_pending: 'Your independent assessment is awaiting review.',
};

export default function Dashboard({ csrfToken, diagnosticsEnabled }: { csrfToken: string; diagnosticsEnabled: boolean }) {
  const [data, setData] = useState<Progress | null>(null);
  const [goals, setGoals] = useState<{ id: string; normalized_statement: string }[]>([]);
  const [goalId, setGoalId] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [panel, setPanel] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const load = useCallback(async () => {
    setPending(true); setError('');
    try {
      const response = await fetch(`/api/v1/progress${goalId ? `?goal_id=${encodeURIComponent(goalId)}` : ''}`);
      if (!response.ok) throw new Error('Progress could not be loaded. Your saved work is safe.');
      setData(await response.json());
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }, [goalId]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    fetch('/api/v1/goals').then(response => response.ok ? response.json() : { items: [] })
      .then(value => setGoals(value.items)).catch(() => setError('Your goals could not be loaded.'));
  }, []);
  useEffect(() => { if (panel) heading.current?.focus(); }, [panel]);

  function open() {
    const action = data?.today.action ?? '';
    if (action === 'choose_goal') { document.getElementById('goal-setup')?.scrollIntoView(); document.getElementById('goal-heading')?.focus(); }
    else if (action === 'diagnostic') setPanel('diagnostic');
    else if (action === 'assessment') setPanel('assessment');
    else if (action === 'start_session' || action === 'resume_session') setPanel('session');
    else if (action === 'program_complete') setPanel('evidence');
    else setPanel('plan');
  }

  const actionable = data && !['waitlist', 'rest', 'today_complete', 'content_unavailable', 'review_pending', 'assessment_review_pending', 'learning_unavailable'].includes(data.today.action);
  return <section aria-label="Learning progress" aria-busy={pending} className="space-y-5 border-b border-base-300 pb-6">
    <div className="flex flex-wrap items-center justify-between gap-3">
      <h2 className="text-2xl font-bold">Today and your progress</h2>
      <button className="btn" onClick={() => { setPanel(''); void load(); }} disabled={pending}>Refresh progress</button>
    </div>
    {goals.length > 1 && <label className="flex flex-col gap-2">Learning goal
      <select className="border border-base-300 rounded-field p-3 w-full" value={goalId} onChange={event => { setGoalId(event.target.value); setPanel(''); }}>
        <option value="">Most recent goal</option>{goals.map(goal => <option key={goal.id} value={goal.id}>{goal.normalized_statement}</option>)}
      </select></label>}
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    {!data && !error && <p role="status">Loading your learning evidence…</p>}
    {data && <>
      {data.statement && <div><p className="font-semibold">{data.statement}</p>
        <p className="text-sm">{label(data.track ?? '')} · {label(data.language ?? '')} · {data.target_date === 'no_fixed_date' ? 'No fixed target date' : `Target: ${data.target_date}`}</p>
        {data.plan && <p>Trajectory: {label(data.plan.feasibility)}. This is a workload estimate, not a guaranteed outcome.</p>}</div>}
      <div className="card card-border"><div className="card-body">
        <h3 className="card-title">{actions[data.today.action] ?? 'Review your next step'}</h3>
        {!!data.today.minutes && <p>About {data.today.minutes} minutes for retrieval, focused practice and an independent check.</p>}
        {data.local_date && <p className="text-sm">{data.local_date} · {data.timezone}</p>}
        {actionable && <div className="card-actions"><button className="btn btn-neutral" onClick={open} disabled={pending}>{actions[data.today.action]}</button></div>}
        {data.assessment_due && <p>{label(data.assessment_due.kind)} check {data.assessment_due.deferred_until ? `deferred until ${new Date(data.assessment_due.deferred_until * 1000).toLocaleString()}` : 'is due'}.</p>}
        {data.today.action === 'assessment' && data.assessment_due?.can_defer && <button className="btn" disabled={pending} onClick={async () => {
          setPending(true); setError('');
          try {
            const response = await fetch(`/api/v1/goals/${data.goal_id}/assessment-deferral`, { method: 'POST',
              headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: JSON.stringify({ cycle: data.assessment_due?.cycle }) });
            if (!response.ok) throw new Error('This assessment could not be deferred. Refresh progress and try again.');
            await load();
          } catch (err) { setError((err as Error).message); setPending(false); }
        }}>Defer once for 24 hours</button>}
      </div></div>
      {!!data.plan?.milestones.length && <p>Next milestone: {Object.entries(data.plan.milestones[0]).map(([key, value]) => `${label(key)}: ${String(value)}`).join(' · ')}</p>}
      {!!data.concepts?.length && <div>
        <h3 className="font-bold">Capability map</h3>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2">{data.concepts.map(concept => <li key={concept.id} className="rounded-box border border-base-300 p-3">
          <p className="font-semibold">{concept.title}</p><p>{label(concept.band)}{concept.retention_due && ' · Retention due'}</p>
          <p className="text-sm">{concept.confidence < .65 ? 'Limited confidence; more independent evidence needed.' : 'Confidence supported by reviewed evidence.'}</p>
          <details className="mt-2"><summary className="cursor-pointer py-2">Evidence for {concept.title}</summary>
            <p>{concept.estimate === null ? 'No evidence yet.' : `Estimate ${Math.round(concept.estimate * 100)}%; confidence ${Math.round(concept.confidence * 100)}%.`}</p>
            <p>{concept.reason_codes.map(label).join(', ')}</p><p className="text-sm">{data.uncertainty}</p>
          </details>
        </li>)}</ul>
      </div>}
      {data.goal_id && <div className="flex flex-wrap gap-3">
        <button className="btn" onClick={() => setPanel('plan')}>Schedule and recovery</button>
        <button className="btn" onClick={() => setPanel('assessment')}>Assessments</button>
        <button className="btn" onClick={() => setPanel('evidence')}>Review learning evidence</button>
      </div>}
      {panel && <div className="border-t border-base-300 pt-5">
        <h3 ref={heading} tabIndex={-1} className="text-xl font-bold">{panel === 'evidence' ? 'Learning evidence' : label(panel)}</h3>
        {data.goal_id && panel === 'diagnostic' && <DiagnosticFlow goalId={data.goal_id} csrfToken={csrfToken} enabled={diagnosticsEnabled} />}
        {data.goal_id && panel === 'plan' && <><p className="mt-3">{data.missed_days ?? 0} missed planned days. Recovery recalculates your workload without adding a backlog. Pause whenever you need rest.</p>
          <ul className="my-3">{data.schedule?.map(day => <li key={day.date}>{day.date}: {label(day.status)} · {day.minutes} minutes</li>)}</ul>
          <Planner goalId={data.goal_id} csrfToken={csrfToken} /></>}
        {data.goal_id && panel === 'assessment' && <AssessmentFlow goalId={data.goal_id} csrfToken={csrfToken} />}
        {data.goal_id && data.plan && panel === 'session' && <TodaySession goalId={data.goal_id} csrfToken={csrfToken} curriculumRevision={data.plan.revision} />}
        {panel === 'evidence' && <div className="mt-3 space-y-4">
          <p>{data.uncertainty}</p>
          <h4 className="font-bold">Independent and assisted solve trends</h4>
          <ul className="space-y-2">{data.trend?.map(week => <li key={week.start}>{week.start} – {week.end}:
            {(['independent', 'assisted'] as const).map(kind => <p key={kind}>{label(kind)}: {week[kind].count} reviewed attempts; {week[kind].solve_rate === null ? 'no solve estimate yet' : `${Math.round(week[kind].solve_rate! * 100)}% solved at ≥80% score`}.</p>)}
          </li>)}</ul>
          <h4 className="font-bold">Assessment comparisons</h4>
          <ul>{data.assessments?.map(item => <li key={item.id}>{label(item.kind)}: {label(item.status)}{item.result?.evidence_current === false ? ' · Evidence was corrected; this score no longer supports mastery.' : item.result?.score !== undefined && ` · ${Math.round(item.result.score * 100)}%`}</li>)}</ul>
          <h4 className="font-bold">Recent capability changes</h4>
          <ul>{data.mastery_changes?.map((item, index) => <li key={index}>{label(item.concept)}: {label(item.before)} → {label(item.after)} · {label(item.reason)}</li>)}</ul>
          <h4 className="font-bold">Recent reviewed evidence</h4>
          <ul className="space-y-2">{data.evidence?.map(item => <li key={item.id}>{item.concept_ids.map(label).join(', ')}: {label(item.mode)} · {item.hint_level === 0 ? 'independent' : `assisted (level ${item.hint_level})`} · {Math.round(item.score * 100)}% · {label(item.reason_code)}</li>)}</ul>
          {!data.evidence?.length && <p>No reviewed evidence for this goal yet.</p>}
        </div>}
        <button className="btn mt-4" onClick={() => { setPanel(''); void load(); }}>Return to Today</button>
      </div>}
    </>}
  </section>;
}
