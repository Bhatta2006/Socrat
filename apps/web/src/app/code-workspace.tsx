'use client';

import { useEffect, useRef, useState } from 'react';
import type * as Monaco from 'monaco-editor';

type Attempt = { id: string; title: string; statement: string; language: string; source: string; revision: number;
  samples: { input: string; expected: string }[] };
type Run = { id: string; status: string; mode: string; result: null | { operational_status: string; reason_code: string;
  cases: { index: number; status: string; wall_ms: number; stdout: string; stderr: string }[] } };
type MonacoWindow = Window & { monaco?: typeof Monaco };
let monacoPromise: Promise<typeof Monaco> | undefined;
function loadMonaco() {
  if (!monacoPromise) monacoPromise = new Promise((resolve, reject) => {
    const win = window as unknown as MonacoWindow;
    if (win.monaco) { resolve(win.monaco); return; }
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/monaco/editor.css'; document.head.appendChild(css);
    const script = document.createElement('script'); script.type = 'module'; script.src = '/monaco/editor.js';
    script.onload = () => { if (win.monaco) resolve(win.monaco); else reject(new Error('Editor initialization failed')); };
    script.onerror = reject; document.head.appendChild(script);
  });
  return monacoPromise;
}
const messages: Record<string, string> = {
  sandbox_unavailable: 'The execution service is unavailable. Your code is saved; please retry later.',
  code_draft_stale: 'Your code changed in another window. Reload the saved attempt before running.',
  execution_quota_exceeded: 'Your run limit has been reached. Wait for pending runs to finish before retrying.',
  attempt_already_submitted: 'This independent attempt has already been submitted. You can still run samples.',
  source_required: 'Add source code before running or submitting.',
  execution_content_withdrawn: 'This exercise is under review. Your code is preserved.',
  timed_window_ended: 'The timed window has ended. Your code is saved; continue in upsolve.',
  timed_block_not_started: 'Start the timed window before running or submitting.',
  session_not_active: 'Resume your learning session before running or submitting.',
  learning_sessions_unavailable: 'Learning sessions are temporarily unavailable. Your code is saved.',
  session_block_locked: 'Complete the earlier session blocks before running this attempt.',
  session_attempt_mismatch: 'This attempt belongs to an earlier session phase. Reload your session.',
  session_day_ended: 'This session’s day has ended. Your saved code remains available.',
};

export default function CodeWorkspace({ goalId, exerciseId, csrfToken, diagnosticAttemptId, sessionAttemptId, executionDisabled = false, saveHandle, onSubmitted }: {
  goalId: string; exerciseId: string; csrfToken: string; diagnosticAttemptId?: string; sessionAttemptId?: string; executionDisabled?: boolean; saveHandle?: { current: (() => Promise<void>) | null }; onSubmitted?: () => void;
}) {
  const [enabled, setEnabled] = useState(false);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [status, setStatus] = useState(''); const [error, setError] = useState('');
  const [pending, setPending] = useState(false); const [stdin, setStdin] = useState('');
  const [font, setFont] = useState(16); const [theme, setTheme] = useState('vs');
  const [history, setHistory] = useState<Run[]>([]);
  const editorHost = useRef<HTMLDivElement>(null);
  const editor = useRef<Monaco.editor.IStandaloneCodeEditor | null>(null);
  const source = useRef(''); const saved = useRef(''); const revision = useRef(0);
  const saveChain = useRef<Promise<void>>(Promise.resolve());
  const creationKey = useRef(crypto.randomUUID());
  const runKey = useRef<{ signature: string; key: string } | null>(null);

  async function request<T>(url: string, method = 'GET', body?: unknown): Promise<T> {
    const response = await fetch(url, { method, credentials: 'same-origin',
      ...(body === undefined ? {} : { headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken }, body: JSON.stringify(body) }) });
    const data = await response.json();
    if (!response.ok) throw new Error(messages[data.error?.code] ?? 'Your work could not be saved or run. Please retry.');
    return data;
  }

  useEffect(() => { let active = true;
    fetch('/api/v1/features').then(response => response.json()).then(value => { if (active) setEnabled(value.code_execution); }).catch(() => setError('The workspace is unavailable.'));
    return () => { active = false; };
  }, []);

  async function open() {
    setPending(true); setError('');
    try {
      const old = sessionAttemptId ? { items: [] } : await request<{ items: { id: string; exercise_id: string; diagnostic_attempt_id: string | null }[] }>(`/api/v1/goals/${goalId}/code-attempts`);
      const existing = sessionAttemptId ? { id: sessionAttemptId } : old.items.find(item => item.exercise_id === exerciseId && item.diagnostic_attempt_id === (diagnosticAttemptId ?? null));
      const value = existing ? await request<Attempt>(`/api/v1/attempts/${existing.id}`) :
        await request<Attempt>(`/api/v1/goals/${goalId}/code-attempts`, 'POST', { exercise_id: exerciseId,
          idempotency_key: creationKey.current, diagnostic_attempt_id: diagnosticAttemptId ?? null });
      source.current = value.source; saved.current = value.source; revision.current = value.revision; setAttempt(value);
      setHistory((await request<{ items: Run[] }>(`/api/v1/attempts/${value.id}/runs`)).items);
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  function autosave() {
    if (!attempt) return Promise.resolve();
    const attemptId = attempt.id;
    const task = saveChain.current.catch(() => undefined).then(async () => {
      if (source.current === saved.current) return;
      const snapshot = source.current;
      const response = await request<{ revision: number }>(`/api/v1/attempts/${attemptId}/draft`, 'PATCH', { source: snapshot, expected_revision: revision.current });
      revision.current = response.revision; saved.current = snapshot;
      setStatus(source.current === snapshot ? 'Code saved.' : 'Saving latest changes…');
    });
    saveChain.current = task; return task;
  }

  useEffect(() => {
    if (!saveHandle) return;
    const save = () => autosave();
    saveHandle.current = save;
    return () => { if (saveHandle.current === save) saveHandle.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt?.id, saveHandle]);

  useEffect(() => {
    if (!attempt || !editorHost.current) return;
    let active = true;
    let change: Monaco.IDisposable | undefined; let blur: Monaco.IDisposable | undefined;
    loadMonaco().then(monaco => {
      if (!active || !editorHost.current) return;
      editor.current = monaco.editor.create(editorHost.current, { value: source.current, language: attempt.language,
        automaticLayout: true, ariaLabel: 'Solution source code', accessibilitySupport: 'on', minimap: { enabled: false },
        wordWrap: 'on', fontSize: font, theme, scrollBeyondLastLine: false, tabSize: 4 });
      change = editor.current.onDidChangeModelContent(() => { source.current = editor.current!.getValue(); setStatus('Unsaved changes.'); });
      blur = editor.current.onDidBlurEditorText(() => { autosave().catch(err => setError((err as Error).message)); });
    }).catch(() => setError('The code editor could not load. Reload to retry.'));
    const interval = setInterval(() => { autosave().catch(err => setError((err as Error).message)); }, 5000);
    return () => { active = false; clearInterval(interval); change?.dispose(); blur?.dispose(); editor.current?.getModel()?.dispose(); editor.current?.dispose(); editor.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt?.id]);

  useEffect(() => { editor.current?.updateOptions({ fontSize: font });
    (window as unknown as MonacoWindow).monaco?.editor.setTheme(theme); }, [font, theme]);
  useEffect(() => {
    if (!attempt || !history.some(run => ['queued', 'running'].includes(run.status))) return;
    const timer = setInterval(async () => {
      try {
        const data = await request<{ items: Run[] }>(`/api/v1/attempts/${attempt.id}/runs`); setHistory(data.items);
        if (data.items.some(run => run.mode === 'submit' && run.status === 'completed')) onSubmitted?.();
      } catch (err) { setError((err as Error).message); }
    }, 1000);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attempt?.id, history.some(run => ['queued', 'running'].includes(run.status))]);

  async function run(mode: 'runs' | 'submit', custom = false) {
    if (!attempt) return;
    setPending(true); setError('');
    try {
      await autosave(); const body = { draft_revision: revision.current, stdin: custom ? stdin : null };
      const signature = JSON.stringify({ mode, ...body });
      if (runKey.current?.signature !== signature) runKey.current = { signature, key: crypto.randomUUID() };
      const value = await request<Run>(`/api/v1/attempts/${attempt.id}/${mode}`, 'POST', { ...body, idempotency_key: runKey.current.key });
      setHistory(old => [value, ...old.filter(item => item.id !== value.id)]); runKey.current = null;
    } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }

  if (!enabled) return null;
  return <section className="card card-border mt-4 min-w-0" aria-label="Coding workspace" aria-busy={pending}>
    <div className="card-body min-w-0"><h4 className="card-title">Coding workspace</h4>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {!attempt ? <button className="btn" disabled={pending} onClick={open}>Open code editor</button> : <>
        <p className="font-semibold">{attempt.title} · {attempt.language}</p><p className="whitespace-pre-wrap">{attempt.statement}</p>
        <div className="flex flex-wrap gap-3"><label>Font size <input className="input w-24" type="number" min={12} max={28} value={font} onChange={event => setFont(Math.max(12, Math.min(28, Number(event.target.value))))} /></label>
          <label>Editor contrast <select className="select" value={theme} onChange={event => setTheme(event.target.value)}><option value="vs">Light</option><option value="vs-dark">Dark</option><option value="hc-black">High contrast</option></select></label></div>
        <div ref={editorHost} className="h-80 w-full min-w-0 overflow-hidden" data-testid="code-editor" />
        <p role="status">{status || 'Code saved.'}</p>
        <p>Samples: {attempt.samples.map((sample, index) => <span key={index}>{JSON.stringify(sample.input)} → {JSON.stringify(sample.expected)}. </span>)}</p>
        <label>Custom input <textarea className="textarea w-full" maxLength={8000} value={stdin} onChange={event => setStdin(event.target.value)} /></label>
        <div className="flex flex-wrap gap-3"><button className="btn" disabled={pending || executionDisabled} onClick={() => run('runs')}>Run samples</button>
          <button className="btn" disabled={pending || executionDisabled} onClick={() => run('runs', true)}>Run custom input</button>
          <button className="btn" disabled={pending || executionDisabled} onClick={() => run('submit')}>Submit independent attempt</button></div>
        <p>Sample runs do not change mastery. Hidden-test inputs and output are kept private.</p>
        {history.map(item => <article className="card card-border" key={item.id}><div className="card-body p-3"><p>{item.mode} · {item.status}</p>
          {item.result?.operational_status === 'failed' && <p>Your code is preserved. This execution produced no learning evidence.</p>}
          {item.result?.cases.map(test => <div key={test.index}><p>Case {test.index + 1}: {test.status.replaceAll('_', ' ')} · {test.wall_ms} ms</p>
            {test.stdout && <pre className="whitespace-pre-wrap break-all">{test.stdout}</pre>}{test.stderr && <pre className="whitespace-pre-wrap break-all">{test.stderr}</pre>}</div>)}
        </div></article>)}
      </>}
    </div>
  </section>;
}
