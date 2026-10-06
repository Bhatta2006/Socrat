'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import CodeWorkspace from './code-workspace';

type Kind = 'baseline' | 'weekly' | 'final' | 'retention';
type Item = { id: string; exercise_id: string; title: string; statement: string;
  modality: string; response_kind: string; choices: { id: string; label: string }[];
  rubric_criteria: string[]; status: string };
type Assessment = { id: string; kind: Kind; status: string; revision: number;
  deadline_at: number; items: Item[]; independence: string;
  result: null | { status: string; score?: number; passed?: boolean; reason_code?: string; evidence_current?: boolean; dispute_pending?: boolean } };
const messages: Record<string, string> = {
  fresh_assessment_form_unavailable: 'A fresh reviewed form is not available for this goal yet.',
  baseline_required: 'Complete your baseline before starting later checks.',
  baseline_already_completed: 'Your baseline is already complete.',
  weekly_not_due: 'Your next weekly check is not due yet.',
  retention_not_due: 'No retention check is due yet.',
  retention_policy_review_required: 'The spaced review policy needs a reviewed activation before retention checks are available.',
  assessment_already_active: 'Resume your current assessment first.',
  assessment_response_stale: 'Your saved work changed. Refresh before submitting again.',
  assessment_not_active: 'This form has ended. Refresh to view its status.',
  assessment_responses_pending: 'Submit each response before finishing the form.',
  assessment_content_unavailable: 'This form is under review. Your saved work is preserved.',
};

export default function AssessmentFlow({ goalId, csrfToken }: { goalId: string; csrfToken: string }) {
  const [enabled, setEnabled] = useState(false);
  const [history, setHistory] = useState<Assessment[]>([]);
  const [current, setCurrent] = useState<Assessment | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [due, setDue] = useState(0);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [clock, setClock] = useState(0);
  const startKey = useRef<{ kind: Kind; key: string } | null>(null);
  const responseKey = useRef<{ signature: string; key: string } | null>(null);

  const request = useCallback(async <T,>(path: string, body?: unknown): Promise<T> => {
    const response = await fetch(path, { credentials: 'same-origin', ...(body === undefined ? {} : {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify(body),
    }) });
    const data = await response.json();
    if (!response.ok) throw new Error(messages[data.error?.code] ?? 'Your assessment could not be saved. Please retry.');
    return data;
  }, [csrfToken]);

  const load = useCallback(async () => {
    const [records, retention] = await Promise.all([
      request<{ items: Assessment[] }>(`/api/v1/goals/${goalId}/assessments`),
      request<{ items: unknown[] }>(`/api/v1/goals/${goalId}/retention`),
    ]);
    setHistory(records.items); setDue(retention.items.length);
    return records.items;
  }, [goalId, request]);

  useEffect(() => { let alive = true;
    fetch('/api/v1/features').then(r => r.json()).then(async features => {
      if (!alive || !features.assessments) return;
      setEnabled(true);
      const records = await load();
      if (alive) setCurrent(records.find(x => !x.result) ?? null);
    }).catch(() => { if (alive) setError('Assessment availability could not be checked.'); });
    return () => { alive = false; };
  }, [load]);

  useEffect(() => {
    setClock(Math.floor(Date.now() / 1000));
    const timer = setInterval(() => setClock(Math.floor(Date.now() / 1000)), 1000);
    return () => clearInterval(timer);
  }, []);

  async function action(work: () => Promise<void>) {
    setPending(true); setError('');
    try { await work(); } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function refresh() {
    if (!current) return;
    setCurrent(await request<Assessment>(`/api/v1/assessments/${current.id}`));
    await load();
  }

  async function start(kind: Kind) {
    if (startKey.current?.kind !== kind) startKey.current = { kind, key: crypto.randomUUID() };
    setCurrent(await request<Assessment>(`/api/v1/goals/${goalId}/assessments`, { kind, idempotency_key: startKey.current.key }));
    startKey.current = null; setAnswers({}); await load();
  }

  async function submit(item: Item, report = false) {
    if (!current) return;
    const answer = answers[item.id] ?? '';
    const signature = JSON.stringify([current.id, item.id, current.revision, answer, report]);
    if (responseKey.current?.signature !== signature) responseKey.current = { signature, key: crypto.randomUUID() };
    setCurrent(await request<Assessment>(`/api/v1/assessments/${current.id}/responses`, {
      item_id: item.id, revision: current.revision, answer, report_problem: report,
      idempotency_key: responseKey.current.key,
    }));
    responseKey.current = null;
  }

  if (!enabled) return null;
  const active = current?.status === 'in_progress' && !current.result && clock < current.deadline_at;
  return <section className="mt-6 space-y-4 border-t border-base-300 pt-6" aria-busy={pending}>
    <h3 className="text-xl font-bold">Independent assessments</h3>
    <p>Check what you can do on unfamiliar problems. Retention checks revisit it later.</p>
    <p role="status">{due} concepts due for retention.</p>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    <div className="flex flex-wrap gap-2">
      {(['baseline', 'weekly', 'final', 'retention'] as Kind[]).map(kind => <button type="button" className="btn" key={kind}
        disabled={pending || !!current && !current.result && current.status !== 'expired'}
        onClick={() => action(() => start(kind))}>Start {kind} check</button>)}
    </div>
    {history.length > 0 && <label className="block">Saved assessments
      <select className="select mt-2 w-full" value={current?.id ?? ''} disabled={pending}
        onChange={event => { setCurrent(history.find(x => x.id === event.target.value) ?? null); setAnswers({}); }}>
        <option value="">Choose an assessment</option>
        {history.map(x => <option key={x.id} value={x.id}>{x.kind} — {x.status.replaceAll('_', ' ')}</option>)}
      </select>
    </label>}
    {current && <div className="space-y-4">
      <p>{current.independence}</p>
      <p>Status: {current.status.replaceAll('_', ' ')}. {active ? `${Math.max(0, Math.ceil((current.deadline_at - clock) / 60))} minutes remaining.` : ''}</p>
      {current.result && <div className="alert" role="status">{current.result.status === 'scored'
        ? `Form ${current.result.passed ? 'passed' : 'completed below its pass threshold'}. ${Math.round((current.result.score ?? 0) * 100)}% independently assessed. Mastery also requires diverse evidence, prerequisites, and delayed retention.`
        : 'This form is unscored. Start a fresh reviewed form when available; your earlier work is preserved.'}</div>}
      {current.status === 'pending_review' && <div className="alert" role="status">A reviewer must check this form before it changes mastery.</div>}
      {current.result?.dispute_pending && <div className="alert" role="status">Your dispute is waiting for independent review.</div>}
      {current.result?.evidence_current === false && <div className="alert" role="status">This historical result includes corrected evidence. Current mastery uses the correction.</div>}
      {current.items.map(item => <div className="card card-border" key={item.id}><div className="card-body">
        <h4 className="card-title">{item.title}</h4><p className="whitespace-pre-wrap">{item.statement}</p>
        <p>Status: {item.status.replaceAll('_', ' ')}</p>
        {active && item.status === 'available' && (item.modality === 'code'
          ? <CodeWorkspace goalId={goalId} exerciseId={item.exercise_id} assessmentItemId={item.id}
              csrfToken={csrfToken} onSubmitted={() => action(refresh)} />
          : <label>Your response
              {item.choices.length ? <select className="select mt-2 w-full" value={answers[item.id] ?? ''}
                onChange={event => setAnswers({ ...answers, [item.id]: event.target.value })}>
                <option value="">Choose an answer</option>{item.choices.map(x => <option key={x.id} value={x.id}>{x.label}</option>)}
              </select> : <textarea className="textarea mt-2 w-full" maxLength={2000} value={answers[item.id] ?? ''}
                onChange={event => setAnswers({ ...answers, [item.id]: event.target.value })} />}
              {item.rubric_criteria.length > 0 && <span className="mt-2 block">Explain: {item.rubric_criteria.join(', ').replaceAll('_', ' ')}.</span>}
            </label>)}
        {active && item.status === 'available' && <div className="card-actions">
          {item.modality !== 'code' && <button type="button" className="btn" disabled={pending || !answers[item.id]?.trim()}
            onClick={() => action(() => submit(item))}>Submit response</button>}
          <button type="button" className="btn" disabled={pending} onClick={() => action(() => submit(item, true))}>Report ambiguous item</button>
        </div>}
        {current.result?.status === 'scored' && <label>Explain a scoring concern
          <textarea className="textarea mt-2 w-full" maxLength={2000} value={answers[item.id] ?? ''}
            onChange={event => setAnswers({ ...answers, [item.id]: event.target.value })} />
          <button type="button" className="btn mt-2" disabled={pending || !answers[item.id]?.trim()} onClick={() => action(async () => {
            setCurrent(await request<Assessment>(`/api/v1/assessments/${current.id}/items/${item.id}/dispute`, {
              idempotency_key: `dispute-${item.id}`, rationale: answers[item.id],
            }));
          })}>Request scoring review</button>
        </label>}
      </div></div>)}
      <div className="flex flex-wrap gap-2">
        <button type="button" className="btn" disabled={pending} onClick={() => action(refresh)}>Refresh saved status</button>
        {!current.result && <button type="button" className="btn" disabled={pending} onClick={() => action(async () => {
          setCurrent(await request<Assessment>(`/api/v1/assessments/${current.id}/complete`, {})); await load();
        })}>Finish assessment</button>}
      </div>
    </div>}
  </section>;
}
