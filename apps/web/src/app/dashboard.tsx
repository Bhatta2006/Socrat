'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useLearner } from './learner-context';

type Rate = { count: number; solve_rate: number | null };
type Progress = { goal_id: string | null; statement?: string; track?: string; language?: string; local_date?: string; timezone?: string; uncertainty?: string; missed_days?: number;
  today: { action: string; minutes?: number; session_id?: string | null };
  plan?: { revision: number; status: string; feasibility: string; milestones: { concept_id?: string; date?: string }[] } | null;
  concepts?: { id: string; title: string; band: string; confidence: number; retention_due: boolean; estimate: number | null; reason_codes: string[] }[];
  schedule?: { date: string; status: string; minutes: number }[];
  trend?: { start: string; end: string; independent: Rate; assisted: Rate }[];
  evidence?: { id: string; concept_ids: string[]; score: number; mode: string; hint_level: number; occurred_at: number; reason_code: string }[];
  assessments?: { id: string; kind: string; status: string; result: { score?: number; evidence_current?: boolean } | null }[];
  mastery_changes?: { concept: string; before: string; after: string; reason: string }[];
  assessment_due?: { kind: string; cycle: string; can_defer: boolean; deferred_until: number | null; actionable: boolean } | null;
};
const label = (v: string) => v.replaceAll('_', ' ');
const actions: Record<string, [string, string]> = {
  choose_goal: ['Choose your learning goal', '/onboarding'], diagnostic: ['Take your diagnostic', '/diagnostic'],
  generate_plan: ['Create your learning plan', '/plan'], confirm_plan: ['Review and confirm your plan', '/plan'],
  refresh_plan: ['Refresh your plan', '/plan'], recover: ['Choose a comfortable recovery plan', '/plan'], resume_plan: ['Resume your plan', '/plan'],
  start_session: ['Start today’s session', '/session/today'], resume_session: ['Resume today’s session', '/session/today'],
  assessment: ['Take your independent assessment', '/assessments'], program_complete: ['Review your program evidence', '/progress'],
};
const calmStates: Record<string, string> = { rest: 'A planned rest day', today_complete: 'Today’s session is complete',
  waitlist: 'Your chosen target needs more content. You can choose a supported foundations goal.',
  content_unavailable: 'This learning content needs attention. Your work is preserved and mastery has not changed.',
  review_pending: 'Your diagnostic needs a review before the next step.',
  learning_unavailable: 'Practice needs attention. Your work is preserved and mastery has not changed.',
  assessment_review_pending: 'Your assessment needs a review. Your earlier evidence is preserved.' };

export default function Dashboard({ view = 'today' }: { view?: 'today' | 'progress' }) {
  const { profile, goal } = useLearner(); const [data, setData] = useState<Progress | null>(null); const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    setBusy(true); setError('');
    try { const response = await fetch(`/api/v1/progress${goal ? `?goal_id=${encodeURIComponent(goal.id)}` : ''}`); if (!response.ok) throw new Error(); setData(await response.json()); }
    catch { setError('Your progress could not connect. Your work is preserved and mastery has not changed.'); }
    finally { setBusy(false); }
  }, [goal]);
  useEffect(() => { if (profile) void load(); }, [profile, load]);
  if (error) return <div role="alert" className="alert"><p>{error}</p><button className="btn" onClick={() => void load()}>Try again</button></div>;
  if (!data) return <p role="status">Loading your learning evidence…</p>;
  const next = actions[data.today.action];
  const milestone = data.plan?.milestones[0];
  return <section className="dashboard" aria-busy={busy} aria-label="Learning progress">
    <div className="goal-line"><div><p className="eyebrow">{label(data.track ?? 'Your learning path')} · {data.language ?? 'Choose a language'}</p><p>{data.statement ?? 'A clear next step begins with a goal.'}</p></div><button className="btn btn-sm" onClick={() => void load()}>Refresh progress</button></div>
    {view === 'today' ? <>
      <section className="next-step"><div><p className="eyebrow">Your next step</p><h2>{next?.[0] ?? calmStates[data.today.action] ?? 'Review your next step'}</h2><p>{data.today.minutes ? `About ${data.today.minutes} minutes. Retrieval, practice, and an independent check.` : 'Your plan follows your saved evidence and the time you have.'}</p>{data.plan && <p className="subtle">Trajectory: {label(data.plan.feasibility)}. A workload estimate, not a guaranteed outcome.</p>}</div>
        {next && <Link className="btn btn-primary" href={data.today.session_id && ['start_session', 'resume_session'].includes(data.today.action) ? `/session/${data.today.session_id}` : next[1]}>{next[0]} <span aria-hidden="true">→</span></Link>}
        {data.today.action === 'waitlist' && <Link className="btn" href="/onboarding">Choose a foundations goal</Link>}
      </section>
      {milestone && <p className="milestone">Next milestone: <strong>{data.concepts?.find(x => x.id === milestone.concept_id)?.title ?? label(milestone.concept_id ?? 'independent practice')}</strong>{milestone.date && ` · ${milestone.date}`}</p>}
      {!!data.concepts?.length && <section className="capability-section"><div className="section-heading"><h2>Your capability map</h2><Link href="/progress">See the evidence →</Link></div><ul className="capability-map">{data.concepts.map(c => <li key={c.id} className={`capability-node band-${c.band}`}><span className="capability-symbol" aria-hidden="true">{c.band === 'mastered' ? '✓' : c.estimate === null ? '○' : '◐'}</span><div><h3>{c.title}</h3><p>{label(c.band)}{c.retention_due ? ' · Retention due' : c.confidence < .65 ? ' · Limited confidence' : ' · Supported confidence'}</p></div></li>)}</ul></section>}
      {!!data.schedule?.length && <section><div className="section-heading"><h2>Your next seven days</h2><Link href="/plan">Adjust your schedule →</Link></div><ol className="week-schedule">{data.schedule.slice(0, 7).map(day => <li key={day.date}><time dateTime={day.date}>{new Date(day.date + 'T12:00:00').toLocaleDateString('en', { weekday: 'short', day: 'numeric' })}</time><strong>{day.minutes ? `${day.minutes} min` : 'Rest'}</strong><span>{label(day.status)}</span></li>)}</ol></section>}
      {data.assessment_due?.can_defer && data.today.action === 'assessment' && <button className="btn" onClick={async () => { const response = await fetch(`/api/v1/goals/${data.goal_id}/assessment-deferral`, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile?.csrf_token ?? '' }, body: JSON.stringify({ cycle: data.assessment_due?.cycle }) }); if (!response.ok) setError('The assessment could not be deferred. Refresh and try again.'); else await load(); }}>Defer once for 24 hours</button>}
    </> : <>
      <p className="lede">{data.uncertainty}</p><section className="surface"><h2>Independent and assisted solve trends</h2>
        <div className="trend-chart" role="img" aria-label="Solve rates by week; exact values in the table below">{data.trend?.map(week => <div className="trend-week" key={week.start}><div className="trend-bars">{(['independent', 'assisted'] as const).map(kind => <div className={`trend-bar ${kind}`} key={kind} style={{ height: `${Math.max(2, (week[kind].solve_rate ?? 0) * 100)}%` }}><span>{week[kind].count} {kind}</span></div>)}</div><span>{week.start}</span></div>)}</div>
        <div className="table-scroll"><table className="table"><caption>Verified solve rates by assistance level</caption><thead><tr><th>Week</th><th>Independent attempts</th><th>Independent solve rate</th><th>Assisted attempts</th><th>Assisted solve rate</th></tr></thead><tbody>{data.trend?.map(w => <tr key={w.start}><th>{w.start}</th><td>{w.independent.count}</td><td>{w.independent.solve_rate === null ? 'No evidence yet' : `${Math.round(w.independent.solve_rate * 100)}%`}</td><td>{w.assisted.count}</td><td>{w.assisted.solve_rate === null ? 'No evidence yet' : `${Math.round(w.assisted.solve_rate * 100)}%`}</td></tr>)}</tbody></table></div></section>
      <section className="surface"><h2>Assessment comparisons</h2>{data.assessments?.length ? <ul className="evidence-list">{data.assessments.map(x => <li key={x.id}>{label(x.kind)} · {label(x.status)} · {x.result?.evidence_current === false ? 'Evidence corrected; no longer supports mastery' : x.result?.score === undefined ? 'No score yet' : `${Math.round(x.result.score * 100)}%`}</li>)}</ul> : <p>Complete an independent assessment to compare your results.</p>}</section>
      <section className="surface"><h2>Recent capability changes</h2>{data.mastery_changes?.length ? <ul className="evidence-list">{data.mastery_changes.map((x, i) => <li key={i}><strong>{label(x.concept)}</strong>: {label(x.before)} → {label(x.after)}<p>{label(x.reason)}</p></li>)}</ul> : <p>Capability changes appear here when verified work changes your evidence.</p>}</section>
      <section className="surface"><h2>Recent reviewed evidence</h2>{data.evidence?.length ? <ul className="evidence-list">{data.evidence.map(x => <li key={x.id}><strong>{x.concept_ids.map(label).join(', ')}</strong><p>{label(x.mode)} · {x.hint_level === 0 ? 'independent' : `assisted (level ${x.hint_level})`} · {Math.round(x.score * 100)}% · {label(x.reason_code)}</p></li>)}</ul> : <p>No reviewed evidence for this goal yet. Complete your starting check or a practice session to begin.</p>}</section>
      <details className="surface"><summary>Capability estimates and confidence</summary>{data.concepts?.map(c => <p key={c.id}>{c.title}: {label(c.band)} · {Math.round(c.confidence * 100)}% confidence · {c.reason_codes.map(label).join(', ')}</p>)}</details>
    </>}
  </section>;
}
