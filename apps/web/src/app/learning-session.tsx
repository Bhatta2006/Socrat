'use client';

import { useEffect, useRef, useState } from 'react';
import CodeWorkspace from './code-workspace';

type Block = { mode: string; title: string; minutes: number; modality: string; status: string;
  exercise_ids: string[]; attempt_id?: string;
  timed: boolean; deadline_at?: number; timed_outcome?: { outcome: string; score?: number };
  error_classification?: string;
  content: { prompt: string; explanations: string[]; examples: string[] } };
type LearningSession = { id: string; revision: number; status: string; local_date: string;
  track: string; language: string; planned_minutes: number; timing: string; server_now?: number; blocks: Block[] };
const label = (value: string) => value.replaceAll('_', ' ');
const messages: Record<string, string> = {
  plan_evidence_stale: 'New evidence changed your plan. Refresh and confirm it before starting.',
  reviewed_plan_required: 'Confirm your learning plan before continuing.',
  no_session_today: 'Today is a rest day or reviewed practice is unavailable.',
  session_revision_stale: 'Your session changed in another window. Reload today’s session.',
  verified_submit_required: 'Submit your solution and wait for a scored result before continuing.',
  session_content_unavailable: 'This content is under review. Your work is preserved.',
  sandbox_unavailable: 'Code execution is unavailable. Your saved work is preserved.',
  timed_session_not_available: 'Timed practice is still being prepared for this track.',
  session_day_ended: 'This session’s day has ended. Refresh your plan for today.',
  timed_window_ended: 'The timed window has ended. Continue in upsolve with your work saved.',
  timed_block_not_started: 'Start the timed window before submitting this block.',
  timed_block_cannot_pause: 'The timed window keeps running. You can continue in upsolve afterward.',
  timed_submit_pending: 'Your on-time submission is still being scored. Wait for its result.',
  timed_window_active: 'The timed window is still active. Try independently before starting upsolve.',
  upsolve_required: 'Review what went wrong and continue in upsolve.',
  upsolve_not_required: 'Your timed submission passed. Continue to reflection.',
  session_timing_already_chosen: 'Timing was chosen when this session started. Reload the saved session.',
};

export default function TodaySession({ goalId, csrfToken, curriculumRevision }: {
  goalId: string; csrfToken: string; curriculumRevision: number;
}) {
  const [enabled, setEnabled] = useState(false);
  const [session, setSession] = useState<LearningSession | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [answer, setAnswer] = useState('');
  const [reflection, setReflection] = useState('none');
  const [timing, setTiming] = useState('standard');
  const [errorClass, setErrorClass] = useState('time_pressure');
  const [clock, setClock] = useState(Date.now());
  const clockAnchor = useRef({ server: 0, local: 0 });
  const key = useRef<{ signature: string; value: string } | null>(null);
  const saveCode = useRef<(() => Promise<void>) | null>(null);

  async function request<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(path, { credentials: 'same-origin',
      ...(body === undefined ? {} : { method: 'POST', headers: {
        'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken,
      }, body: JSON.stringify(body) }) });
    const value = await response.json();
    if (!response.ok) throw new Error(messages[value.error?.code] ?? 'Your session could not be saved. Please retry.');
    return value;
  }

  async function reload() {
    setPending(true); setError('');
    try { setSession((await request<{ session: LearningSession | null }>(`/api/v1/goals/${goalId}/learning-session`)).session); }
    catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  useEffect(() => {
    let active = true;
    fetch('/api/v1/features').then(response => response.json()).then(async features => {
      if (!active || !features.learning_sessions) return;
      setEnabled(true);
      const value = await request<{ session: LearningSession | null }>(`/api/v1/goals/${goalId}/learning-session`);
      if (active) setSession(value.session);
    }).catch(() => { if (active) setError('Today’s session could not be loaded.'); });
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goalId]);

  useEffect(() => {
    clockAnchor.current = { server: session?.server_now ?? Date.now() / 1000, local: Date.now() };
    setClock(Date.now());
    const timer = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [session?.server_now, session?.revision]);

  async function act(action: string, runId?: string) {
    setPending(true); setError('');
    try {
      await saveCode.current?.();
      if (!session) {
        setSession(await request<LearningSession>(`/api/v1/goals/${goalId}/learning-session`, {
          curriculum_revision: curriculumRevision,
          timing,
        }));
        return;
      }
      const block = session.blocks.find(item => item.status === 'available');
      const body = { action, expected_revision: session.revision,
        ...(action === 'upsolve' ? { error_classification: errorClass } : {}),
        ...(action === 'advance' ? {
          ...(block?.mode === 'instruction' || runId ? {} : { answer }),
          ...(runId ? { run_id: runId } : {}),
          ...(block?.mode === 'exit_check' ? { reflection } : {}),
        } : {}),
      };
      const signature = JSON.stringify(body);
      if (key.current?.signature !== signature) key.current = { signature, value: crypto.randomUUID() };
      const outcome = await request<LearningSession>(`/api/v1/learning-sessions/${session.id}/commands`, {
        ...body, idempotency_key: key.current.value,
      });
      setSession(outcome);
      if (outcome.server_now !== undefined) {
        setSession((await request<{ session: LearningSession }>(`/api/v1/goals/${goalId}/learning-session`)).session);
      }
      key.current = null; setAnswer('');
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function finishCode() {
    const block = session?.blocks.find(item => item.status === 'available');
    if (!block?.attempt_id) return;
    try {
      const runs = await request<{ items: { id: string; mode: string; status: string }[] }>(`/api/v1/attempts/${block.attempt_id}/runs`);
      const submitted = runs.items.find(run => run.mode === 'submit' && run.status === 'completed');
      if (!submitted) throw new Error(messages.verified_submit_required);
      await act('advance', submitted.id);
    } catch (err) { setError((err as Error).message); }
    finally {
      try { setSession((await request<{ session: LearningSession }>(`/api/v1/goals/${goalId}/learning-session`)).session); }
      catch (err) { setError(previous => previous || (err as Error).message); }
    }
  }

  if (!enabled) return null;
  const block = session?.blocks.find(item => item.status === 'available');
  const code = ['independent', 'upsolve'].includes(block?.mode ?? '') && block?.modality === 'code';
  const timed = Boolean(block?.timed);
  const waitingForTimer = timed && block?.deadline_at === undefined;
  const serverClock = clockAnchor.current.server + (clock - clockAnchor.current.local) / 1000;
  const remaining = Math.max(0, Math.ceil((block?.deadline_at ?? serverClock) - serverClock));
  const expired = timed && !waitingForTimer && remaining === 0;
  const needsUpsolve = timed && !waitingForTimer && (expired || ['unsuccessful', 'unscored_operational_failure'].includes(block?.timed_outcome?.outcome ?? ''));
  return <section className="card card-border" aria-label="Today’s learning session" aria-busy={pending}>
    <div className="card-body">
      <h3 className="card-title">Today</h3>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!session ? <><p>Start a session from your reviewed plan. Your progress is saved as you work.</p>
        <label>Practice timing
          <select className="select w-full" value={timing} onChange={event => setTiming(event.target.value)}>
            <option value="standard">Use planned timing</option>
            <option value="untimed">Untimed practice</option>
          </select>
        </label>
        <p className="text-sm">Untimed practice is available when time pressure is a barrier. It is recorded separately from timed performance.</p>
        <button className="btn" disabled={pending} onClick={() => act('start')}>Start today’s session</button></> : <>
        <p role="status">{label(session.track)} · {session.language} · {session.planned_minutes} min · {label(session.status)}</p>
        {session.timing === 'untimed' && <p>Untimed practice</p>}
        <ol className="space-y-1">{session.blocks.map(item => <li key={item.mode}>{label(item.mode)} · {item.minutes} min · {label(item.status)}</li>)}</ol>
        {session.status === 'completed' && <p>Your learning session is complete. Reading and reflection do not prove mastery; coding results are recorded separately.</p>}
        {session.status === 'paused' && <button className="btn" disabled={pending} onClick={() => act('resume')}>Resume session</button>}
        {block && session.status === 'in_progress' && <>
          <h4 className="font-semibold">{label(block.mode)}: {block.title}</h4>
          <p className="whitespace-pre-wrap">{block.content.prompt}</p>
          {waitingForTimer && <><p>The {block.minutes}-minute window starts when you choose Start timed practice. Reloading will keep its original deadline.</p>
            <button className="btn" disabled={pending} onClick={() => act('start_timed')}>Start timed practice</button></>}
          {timed && !waitingForTimer && <p aria-label="Time remaining">{expired ? 'Timed window ended. Your code is saved.' : `Time remaining: ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`}</p>}
          {block.timed_outcome && <p>Timed outcome: {label(block.timed_outcome.outcome)}</p>}
          {block.mode === 'upsolve' && <p>Upsolve: repair your saved solution without the timer. This repeats a seen problem and does not create another timed result. Error category: {label(block.error_classification ?? '')}.</p>}
          {block.content.explanations.map((text, index) => <p className="whitespace-pre-wrap" key={index}>{text}</p>)}
          {block.content.examples.map((text, index) => <pre className="overflow-auto whitespace-pre-wrap" key={index}>{text}</pre>)}
          {!waitingForTimer && (code ? <><CodeWorkspace key={block.attempt_id} goalId={goalId} exerciseId={block.exercise_ids[0]}
            csrfToken={csrfToken} sessionAttemptId={block.attempt_id} executionDisabled={expired} saveHandle={saveCode} />
            <button className="btn" disabled={pending} onClick={finishCode}>Continue after Submit</button></> : <>
            {block.mode !== 'instruction' && <label>Your response
              <textarea className="textarea w-full" value={answer} maxLength={8000} onChange={event => setAnswer(event.target.value)} />
            </label>}
            {block.mode === 'exit_check' && <label>What made this task difficult?
              <select className="select w-full" value={reflection} onChange={event => setReflection(event.target.value)}>
                {['none', 'concept_gap', 'pattern_recognition', 'implementation_bug', 'complexity', 'unclear_prompt', 'time_pressure'].map(value => <option value={value} key={value}>{label(value)}</option>)}
              </select>
            </label>}
            <button className="btn" disabled={pending || expired || (block.mode !== 'instruction' && !answer.trim())} onClick={() => act('advance')}>Save and continue</button>
            {block.mode !== 'instruction' && <p className="text-sm">Your response is saved without a mastery score.</p>}
          </>)}
          {needsUpsolve && block.timed_outcome?.outcome !== 'solved' && <>
            <label>What should you repair?
              <select className="select w-full" value={errorClass} onChange={event => setErrorClass(event.target.value)}>
                {['time_pressure', 'wrong_answer', 'implementation_bug', 'complexity', 'concept_gap', 'unclear_prompt'].map(value => <option value={value} key={value}>{label(value)}</option>)}
              </select>
            </label>
            <button className="btn" disabled={pending || block.timed_outcome?.outcome === 'pending'} onClick={() => act('upsolve')}>Start upsolve</button>
          </>}
          <div className="card-actions">
            <button className="btn" disabled={pending || (timed && !waitingForTimer)} onClick={() => act('pause')}>Pause session</button>
            <button className="btn" disabled={pending} onClick={() => act('abandon')}>End session early</button>
          </div>
        </>}
      </>}
      <button className="btn" disabled={pending} onClick={reload}>Reload today’s session</button>
    </div>
  </section>;
}
