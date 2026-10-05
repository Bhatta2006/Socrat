'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';
import Planner from './planner';

type ConceptState = { band: string; confidence: number; evidence_count: number; independent_count: number;
  assisted_count: number; reason_codes: string[]; missing_gates: string[];
  misconceptions: Record<string, { resolved: boolean }> };
type Result = { scope: string; placement_sufficient: boolean; full_placement: boolean; missing_evidence: string[];
  stop_reason: string; concepts: Record<string, ConceptState | null>; evidence_current?: boolean };
type Diagnostic = { id: string; status: string; revision: number; answered: number; scope: string;
  deadline_at: number; server_time: number; active_track: string; declared_track: string; result: Result | null;
  item: { attempt_id: string; title: string; statement: string; kind: string; position: number;
    choices: { id: string; label: string }[] } | null };
const label = (value: string) => value.replaceAll('_', ' ');
const messages: Record<string, string> = {
  diagnostic_coverage_unavailable: 'The diagnostic for this goal and language is not released yet.',
  goal_content_unavailable: 'Content availability changed. Your saved goal is preserved; please return when reviewed content is available.',
  diagnostic_response_stale: 'This item changed in another window. Reload to resume your saved work.',
  diagnostic_time_expired: 'The diagnostic time window ended. You can still view your evidence.',
  diagnostic_content_withdrawn: 'This content is being reviewed. Your earlier work is preserved.',
  concurrent_diagnostic_retry: 'Your work is being saved. Please retry the same action.',
};

export default function DiagnosticFlow({ goalId, csrfToken, enabled }: {
  goalId: string; csrfToken: string; enabled: boolean;
}) {
  const [session, setSession] = useState<Diagnostic | null>(null);
  const [answer, setAnswer] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const key = useRef<{ attempt: string; answer: string; report: boolean; value: string } | null>(null);

  async function request<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(path, { credentials: 'same-origin', ...(body !== undefined ? {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      body: JSON.stringify(body),
    } : {}) });
    if (!response.ok) {
      const code = (await response.json()).error?.code as string;
      throw new Error(messages[code] ?? 'Your diagnostic could not be loaded or saved. Please retry.');
    }
    return response.json();
  }

  useEffect(() => {
    let active = true;
    fetch(`/api/v1/goals/${goalId}/diagnostics`, { credentials: 'same-origin' }).then(async response => {
      if (!response.ok) throw new Error('Could not load your diagnostic. Please reload.');
      const data = await response.json();
      if (active) { setSession(data.items[0] ?? null); setAnswer(''); }
    }).catch(err => { if (active) setError((err as Error).message); });
    return () => { active = false; };
  }, [goalId]);

  async function start() {
    setPending(true); setError('');
    try { setSession(await request<Diagnostic>(`/api/v1/goals/${goalId}/diagnostics`, {})); }
    catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function submit(event?: FormEvent, report = false) {
    event?.preventDefault();
    if (!session?.item) return;
    const item = session.item;
    if (!key.current || key.current.attempt !== item.attempt_id || key.current.answer !== answer || key.current.report !== report) {
      key.current = { attempt: item.attempt_id, answer, report, value: crypto.randomUUID() };
    }
    setPending(true); setError('');
    try {
      setSession(await request<Diagnostic>(`/api/v1/diagnostics/${session.id}/responses`, {
        attempt_id: item.attempt_id, revision: session.revision, idempotency_key: key.current.value,
        answer, report_problem: report,
      }));
      setAnswer(''); key.current = null;
      heading.current?.focus();
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function finish() {
    if (!session) return;
    setPending(true); setError('');
    try {
      const result = await request<Result>(`/api/v1/diagnostics/${session.id}/complete`, {});
      setSession({ ...session, item: null, result }); heading.current?.focus();
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  return <section className="card card-border mt-6" aria-busy={pending} aria-label="Diagnostic">
    <div className="card-body">
      <h3 className="card-title" ref={heading} tabIndex={-1}>{session?.result ? 'Your diagnostic evidence' : 'Your starting check'}</h3>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!session && <>
        <p>Begin with reasoning and language readiness. Being unable to code is a useful starting point.</p>
        <p>This check takes up to 15 minutes for foundations or 45 minutes for experienced routes. Your submitted answers are saved so you can reload and resume within the time window.</p>
        <p>Implementation ability needs a separate coding check. These results show the evidence available so far.</p>
        <button className="btn" type="button" disabled={pending || !enabled} onClick={start}>Start diagnostic</button>
      </>}
      {session && <p>Goal: {label(session.declared_track)}. Starting route: {label(session.active_track)}.</p>}
      {session?.item && !session.result && <>
        <p aria-live="polite">{session.answered} answers saved. Item {session.item.position}.</p>
        <p>Time window ends at {new Date(session.deadline_at * 1000).toLocaleTimeString()}. Reload to check the latest saved state.</p>
        <form onSubmit={event => submit(event)} className="space-y-4">
          <fieldset className="space-y-3" disabled={pending || !enabled}>
            <legend className="font-semibold">{session.item.title}</legend>
            <p className="whitespace-pre-wrap">{session.item.statement}</p>
            {session.item.kind === 'choice' ? session.item.choices.map(choice => <label key={choice.id} className="flex items-center gap-3">
              <input className="radio" type="radio" name={`diagnostic-${session.item!.attempt_id}`} value={choice.id}
                checked={answer === choice.id} onChange={event => setAnswer(event.target.value)} required />{choice.label}
            </label>) : <label className="block">Your response
              <input className="input w-full mt-2" value={answer} maxLength={2000} required onChange={event => setAnswer(event.target.value)} />
            </label>}
          </fieldset>
          <div className="flex flex-wrap gap-3">
            <button className="btn" type="submit" disabled={pending || !enabled || !answer}>Save answer and continue</button>
            <button className="btn" type="button" disabled={pending || !enabled} onClick={() => submit(undefined, true)}>Report unclear item</button>
          </div>
        </form>
      </>}
      {session && !session.item && !session.result && <>
        <div className="alert" role="status">{session.status === 'ready_to_complete' ? 'Your available placement evidence is ready.'
          : session.status === 'pending_review' ? 'Your explanation needs review. It will not change mastery while review is pending.'
          : 'This check has reached a coverage or time limit. Your valid answers are preserved.'}</div>
        <button className="btn" type="button" disabled={pending || !enabled} onClick={finish}>View diagnostic evidence</button>
      </>}
      {!enabled && session && <p role="status">Diagnostic scoring is temporarily paused. Your saved results remain available.</p>}
      {session?.result && <div data-testid="diagnostic-result" className="space-y-4">
        <p>{session.result.placement_sufficient ? 'Readiness placement recorded.' : 'Limited placement: more verified evidence is needed.'}</p>
        {!session.result.full_placement && <p>Implementation ability has not been verified.</p>}
        {session.result.evidence_current === false && <div className="alert" role="status">Some evidence was corrected. A fresh placement review is needed.</div>}
        {Object.entries(session.result.concepts).map(([concept, state]) => <div key={concept} className="rounded-box border border-base-300 p-4">
          <h4 className="font-semibold">{label(concept)}: {label(state?.band ?? 'insufficient_evidence')}</h4>
          {state && <>
            <p>{state.evidence_count} valid activities; {state.independent_count} independent, {state.assisted_count} assisted.</p>
            <p>{state.confidence < .65 ? 'Limited evidence confidence. More diverse independent work is needed.' : 'Evidence comes from several activities and forms.'}</p>
            <details><summary className="cursor-pointer">Evidence and uncertainty</summary>
              <p>This is an estimated capability band. It does not certify mastery.</p>
              <ul className="list-disc pl-5">{state.missing_gates.map(reason => <li key={reason}>{label(reason)}</li>)}</ul>
              {Object.entries(state.misconceptions).filter(([, flag]) => !flag.resolved).map(([code]) => <p key={code}>Observed error pattern: {label(code)}.</p>)}
            </details>
          </>}
        </div>)}
        <Planner goalId={goalId} csrfToken={csrfToken} />
      </div>}
    </div>
  </section>;
}
