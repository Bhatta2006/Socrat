'use client';

import { useEffect, useRef, useState } from 'react';
import CodeWorkspace from './code-workspace';
import { useRouter } from 'next/navigation';
import Link from 'next/link';

type Block = { mode: string; title: string; minutes: number; modality: string; status: string;
  exercise_ids: string[]; attempt_id?: string; original_attempt_id?: string;
  timed: boolean; deadline_at?: number; timed_outcome?: { outcome: string; score?: number };
  error_classification?: string; repair_selection?: string; upsolve_minutes?: number;
  answer?: string;
  check_result?: { score: number; check_id: string };
  content: { prompt: string; explanations: string[]; examples: string[];
    objective_check?: { id: string; kind: string; choices: { id: string; label: string }[] } } };
type LearningSession = { id: string; revision: number; status: string; local_date: string;
  competitive_result?: { wrong_submissions: number; penalty_seconds: number };
  track: string; language: string; planned_minutes: number; upsolve_reserved_minutes?: number; timing: string; server_now?: number; blocks: Block[] };
const label = (value: string) => value.replaceAll('_', ' ');
const messages: Record<string, string> = {
  plan_evidence_stale: 'New evidence changed your plan. Refresh and confirm it before starting.',
  reviewed_plan_required: 'Confirm your learning plan before continuing.',
  no_session_today: 'Today is a rest day or reviewed practice is unavailable.',
  session_revision_stale: 'Your session changed in another window. Reload today’s session.',
  verified_submit_required: 'Submit your solution and wait for a scored result before continuing.',
  session_content_unavailable: 'This content is under review. Your work is preserved.',
  session_lesson_unavailable: 'A reviewed lesson is missing for this track and language. Your plan is preserved.',
  invalid_learning_choice: 'Choose one of the listed answers before continuing.',
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

export default function TodaySession({ goalId, csrfToken, curriculumRevision, sessionId, routed = false }: {
  goalId: string; csrfToken: string; curriculumRevision: number; sessionId?: string; routed?: boolean;
}) {
  const router = useRouter();
  const [enabled, setEnabled] = useState(false);
  const [session, setSession] = useState<LearningSession | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [answer, setAnswer] = useState('');
  const [reflection, setReflection] = useState('none');
  const [timing, setTiming] = useState('standard');
  const [errorClass, setErrorClass] = useState('time_pressure');
  const [clock, setClock] = useState(Date.now());
  const [history, setHistory] = useState<{ id: string; local_date: string; status: string; recovery_required: boolean }[]>([]);
  const [historical, setHistorical] = useState<LearningSession | null>(null);
  const [savedSources, setSavedSources] = useState<Record<string, string>>({});
  const clockAnchor = useRef({ server: 0, local: 0 });
  const key = useRef<{ signature: string; value: string } | null>(null);
  const saveCode = useRef<(() => Promise<void>) | null>(null);
  const phaseHeading = useRef<HTMLHeadingElement | null>(null);
  const sessionStatus = useRef<HTMLParagraphElement | null>(null);
  const previousPhase = useRef('');
  const block = session?.blocks.find(item => item.status === 'available');
  const phase = `${session?.id ?? ''}:${session?.status ?? ''}:${session && block ? session.blocks.indexOf(block) : -1}:${block?.mode ?? ''}`;

  useEffect(() => {
    if (previousPhase.current && previousPhase.current !== phase) {
      (phaseHeading.current ?? sessionStatus.current)?.focus();
    }
    previousPhase.current = phase;
  }, [phase]);

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
    try { setSession((await request<{ session: LearningSession | null }>(`/api/v1/goals/${goalId}/learning-session`)).session); setHistorical(null); }
    catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function loadHistory() {
    setPending(true); setError('');
    try { setHistory((await request<{ items: typeof history }>(`/api/v1/goals/${goalId}/learning-sessions`)).items); }
    catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  async function openSaved(id: string) {
    setPending(true); setError('');
    try {
      const saved = await request<LearningSession>(`/api/v1/learning-sessions/${id}`);
      const sources: Record<string, string> = {};
      for (const item of saved.blocks) {
        for (const attemptId of [item.attempt_id, item.original_attempt_id]) {
          if (attemptId && item.status !== 'locked') {
            sources[attemptId] = (await request<{ source: string }>(`/api/v1/attempts/${attemptId}`)).source;
          }
        }
      }
      setSavedSources(sources); setHistorical(saved);
    }
    catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  useEffect(() => {
    let active = true;
    fetch('/api/v1/features').then(response => response.json()).then(async features => {
      if (!active || !features.learning_sessions) return;
      setEnabled(true);
      const value = sessionId && sessionId !== 'today'
        ? { session: await request<LearningSession>(`/api/v1/learning-sessions/${sessionId}`) }
        : await request<{ session: LearningSession | null }>(`/api/v1/goals/${goalId}/learning-session`);
      if (active) setSession(value.session);
    }).catch(() => { if (active) setError('Today’s session could not be loaded.'); });
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [goalId, sessionId]);

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
        const started = await request<LearningSession>(`/api/v1/goals/${goalId}/learning-session`, {
          curriculum_revision: curriculumRevision,
          timing,
        });
        setSession(started);
        if (routed) router.replace(`/session/${started.id}`);
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
          <select className="select w-full" disabled={pending} value={timing} onChange={event => setTiming(event.target.value)}>
            <option value="standard">Use planned timing</option>
            <option value="untimed">Untimed practice</option>
          </select>
        </label>
        <p className="text-sm">Untimed practice is available when time pressure is a barrier. It is recorded separately from timed performance.</p>
        <button className="btn" disabled={pending} onClick={() => act('start')}>Start today’s session</button></> : <>
        <p role="status" ref={sessionStatus} tabIndex={-1} aria-atomic="true">{label(session.track)} · {session.language} · {session.planned_minutes} min · {label(session.status)}</p>
        {session.timing === 'untimed' && <p>Untimed practice</p>}
        {session.competitive_result && <p>Timed practice: {session.competitive_result.wrong_submissions} wrong submissions · {session.competitive_result.penalty_seconds} penalty seconds. Upsolve keeps the original result.</p>}
        {!!session.upsolve_reserved_minutes && <p>Includes {session.upsolve_reserved_minutes} minutes reserved for optional upsolve. Repair time is a planning guide; it does not start another timer.</p>}
        <ol className="session-stepper" aria-label="Session steps">{session.blocks.map((item, index) => <li key={index} aria-current={item.status === 'available' ? 'step' : undefined}>{label(item.mode)} · {item.minutes} min · {label(item.status)}</li>)}</ol>
        {session.status === 'completed' && <p>Your learning session is complete. Reading and reflection do not prove mastery; coding results are recorded separately.</p>}
        {routed && session.status === 'completed' && <Link className="btn btn-primary" href="/progress">See your learning evidence</Link>}
        {session.status === 'expired' && <p>This session ended at local midnight. Your saved work remains available in past sessions. Refresh and confirm your plan to recover without adding a backlog.</p>}
        {session.blocks.filter(item => item.check_result).map((item, index) => <p role="status" key={`check-${index}`}>
          {label(item.mode.replace('_check', ''))} check: {item.check_result?.score === 1 ? 'Correct' : 'Review this concept'}. This check does not establish mastery.
        </p>)}
        {session.status === 'paused' && <button className="btn" disabled={pending} onClick={() => act('resume')}>Resume session</button>}
        {block && session.status === 'in_progress' && <>
          <h4 className="font-semibold" ref={phaseHeading} tabIndex={-1}>{label(block.mode)}: {block.title}</h4>
          {!code && <p className="whitespace-pre-wrap">{block.content.prompt}</p>}
          {waitingForTimer && <><p>The {block.minutes}-minute window starts when you choose Start timed practice. Reloading will keep its original deadline.</p>
            <button className="btn" disabled={pending} onClick={() => act('start_timed')}>Start timed practice</button></>}
          {timed && !waitingForTimer && <><p role="timer" aria-live="off" aria-label="Time remaining">{expired ? 'Timed window ended. Your code is saved.' : `Time remaining: ${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, '0')}`}</p>
            <p className="sr-only" role="status" aria-atomic="true">{expired ? 'Timed practice has ended. Your work is saved; continue in upsolve.' : remaining <= 60 ? 'One minute or less remains in timed practice.' : ''}</p></>}
          {block.timed_outcome && <p>Timed outcome: {label(block.timed_outcome.outcome)}</p>}
          {block.mode === 'upsolve' && <p>{block.repair_selection === 'concept_matched_variant' ? 'Upsolve: practise the same concepts on a reviewed repair task. Your original solution stays saved.' : 'Upsolve: repair your saved solution.'} This phase has no timer and creates no additional timed result. Error category: {label(block.error_classification ?? '')}.</p>}
          {block.content.explanations.map((text, index) => <p className="whitespace-pre-wrap" key={index}>{text}</p>)}
          {block.content.examples.map((text, index) => <pre className="overflow-auto whitespace-pre-wrap" key={index}>{text}</pre>)}
          {!waitingForTimer && (code ? <><CodeWorkspace key={block.attempt_id} goalId={goalId} exerciseId={block.exercise_ids[0]}
            csrfToken={csrfToken} sessionAttemptId={block.attempt_id} executionDisabled={expired} saveHandle={saveCode} />
            <button className="btn" disabled={pending} onClick={finishCode}>Continue after Submit</button></> : <>
            {block.mode !== 'instruction' && <label>Your response
              {block.content.objective_check?.kind === 'choice' ? <select className="select w-full" disabled={pending} value={answer} onChange={event => setAnswer(event.target.value)}>
                <option value="">Choose an answer</option>
                {block.content.objective_check.choices.map(choice => <option key={choice.id} value={choice.id}>{choice.label}</option>)}
              </select> : <textarea className="textarea w-full" disabled={pending} value={answer} maxLength={8000} onChange={event => setAnswer(event.target.value)} />}
            </label>}
            {block.mode === 'exit_check' && <label>What made this task difficult?
              <select className="select w-full" disabled={pending} value={reflection} onChange={event => setReflection(event.target.value)}>
                {['none', 'concept_gap', 'pattern_recognition', 'implementation_bug', 'complexity', 'unclear_prompt', 'time_pressure'].map(value => <option value={value} key={value}>{label(value)}</option>)}
              </select>
            </label>}
            <button className="btn" disabled={pending || expired || (block.mode !== 'instruction' && !answer.trim())} onClick={() => act('advance')}>Save and continue</button>
            {block.mode !== 'instruction' && <p className="text-sm">{block.content.objective_check ? 'This objective check uses a reviewed answer key. Its result does not establish mastery.' : 'Your response is saved without a mastery score.'}</p>}
          </>)}
          {needsUpsolve && block.timed_outcome?.outcome !== 'solved' && <>
            <label>What should you repair?
              <select className="select w-full" disabled={pending} value={errorClass} onChange={event => setErrorClass(event.target.value)}>
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
      <button className="btn" disabled={pending} onClick={loadHistory}>View past sessions</button>
      {history.length > 0 && <ul>{history.map(item => <li key={item.id}>
        <button className="btn btn-ghost" disabled={pending} onClick={() => openSaved(item.id)}>{item.local_date} · {label(item.status)}</button>
        {item.recovery_required && <span>Refresh your plan for recovery.</span>}
      </li>)}</ul>}
      {historical && <section aria-label="Saved learning session">
        <h4 className="font-semibold">Saved session · {historical.local_date} · {label(historical.status)}</h4>
        <p>Past sessions keep their original content and outcomes. Return to today to continue current work.</p>
        <ol>{historical.blocks.map((item, index) => <li key={index}>{label(item.mode)} · {label(item.status)}
          <p className="whitespace-pre-wrap">{item.content.prompt}</p>
          {item.answer && <p className="whitespace-pre-wrap">Saved response: {item.answer}</p>}
          {item.attempt_id && savedSources[item.attempt_id] !== undefined && <pre className="overflow-auto whitespace-pre-wrap" aria-label="Saved source">{savedSources[item.attempt_id]}</pre>}
          {item.original_attempt_id && savedSources[item.original_attempt_id] !== undefined && <pre className="overflow-auto whitespace-pre-wrap" aria-label="Original timed source">{savedSources[item.original_attempt_id]}</pre>}
        </li>)}</ol>
      </section>}
    </div>
  </section>;
}
