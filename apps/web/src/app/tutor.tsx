'use client';

import { useEffect, useRef, useState } from 'react';

type Hint = { id: string; granted_level: number; fallback: boolean; review_required: boolean;
  fresh_task_required: boolean; response: null | { diagnosis: string; message: string; question: string; code_lines?: number[]; reasoning_quote?: string } };
const errors: Record<string, string> = {
  tutor_submit_pending: 'Wait for your submission to finish before asking for help.',
  code_draft_stale: 'Your code changed in another window. Reload the workspace and try again.',
  tutor_help_locked: 'Hints are locked for this challenge.',
  session_not_active: 'Resume your session before asking for help.',
  session_block_locked: 'This practice block has ended.',
  timed_window_ended: 'Continue in upsolve to ask for help.',
  tutor_turn_limit: 'This conversation has reached its limit. Revisit the saved hints or refresh your plan.',
};

export default function Tutor({ attemptId, csrfToken, save, disabled, onAssistance }: {
  attemptId: string; csrfToken: string; save: () => Promise<number>; disabled: boolean;
  onAssistance: (level: number) => void;
}) {
  const [hints, setHints] = useState<Hint[]>([]);
  const [reasoning, setReasoning] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const receipt = useRef<{ signature: string; key: string } | null>(null);
  const level = Math.max(0, ...hints.map(hint => hint.granted_level));

  useEffect(() => {
    let active = true;
    fetch('/api/v1/features').then(response => response.json()).then(async features => {
      if (!features.tutor || !active) return;
      const response = await fetch(`/api/v1/attempts/${attemptId}/tutor`);
      if (!response.ok) return;
      const data = await response.json();
      if (active) { setHints(data.items); setEnabled(true); onAssistance(data.assistance_level); }
    }).catch(() => { if (active) setError('Saved hints could not load. Reload to retry.'); });
    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId]);

  async function ask(action: 'hint' | 'accessibility' | 'exit') {
    setBusy(true); setError('');
    try {
      const revision = await save();
      const body = { reasoning, requested_level: action === 'exit' ? 5 : Math.min(3, level + 1),
        action, draft_revision: revision };
      const signature = JSON.stringify(body);
      if (receipt.current?.signature !== signature) receipt.current = { signature, key: crypto.randomUUID() };
      const response = await fetch(`/api/v1/attempts/${attemptId}/tutor`, { method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
        body: JSON.stringify({ ...body, idempotency_key: receipt.current.key }) });
      const data = await response.json();
      if (!response.ok) throw new Error(errors[data.error?.code] ?? 'Help is unavailable. Your work is saved; please retry.');
      setHints(old => [...old.filter(hint => hint.id !== data.id), data]);
      onAssistance(Math.max(level, data.granted_level)); receipt.current = null;
    } catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }

  if (!enabled) return null;
  return <section className="card card-border" aria-label="Practice tutor" aria-busy={busy}>
    <div className="card-body">
      <h4 className="card-title">Think it through</h4>
      <p>Share your reasoning for a small hint. Help is recorded with this attempt; it does not prove mastery.</p>
      <label>Your plan and what you tried
        <textarea className="textarea w-full" maxLength={2000} value={reasoning}
          onChange={event => setReasoning(event.target.value)} disabled={busy} />
      </label>
      <div className="card-actions">
        <button className="btn" disabled={busy || disabled || !reasoning.trim()} onClick={() => ask('hint')}>Ask for a hint</button>
        <button className="btn" disabled={busy || disabled || !reasoning.trim()} onClick={() => ask('accessibility')}>I need more accessible help</button>
        <button className="btn" disabled={busy || disabled || !reasoning.trim()} onClick={() => ask('exit')}>End independent attempt and show explanation</button>
      </div>
      {error && <p role="alert">{error}</p>}
      <div aria-live="polite" aria-relevant="additions">
        {hints.map(hint => <article key={hint.id} className="mt-3">
          <p className="font-semibold">Hint level {hint.granted_level}{hint.fallback ? ' · Curated guidance' : ''}</p>
          {hint.response?.diagnosis && <p>{hint.response.diagnosis}</p>}
          {!!hint.response?.code_lines?.length && <p>Code lines: {hint.response.code_lines.join(', ')}</p>}
          {hint.response?.reasoning_quote && <blockquote>{hint.response.reasoning_quote}</blockquote>}
          <p className="whitespace-pre-wrap break-words">{hint.response?.message ?? 'This saved response is no longer retained.'}</p>
          <p>{hint.response?.question}</p>
          {hint.review_required && <p>This help needs review. A review request has been recorded; you can use the reviewed explanation.</p>}
          {hint.fresh_task_required && <p>This is now learning-only. Refresh your plan to find a fresh independent task.</p>}
        </article>)}
      </div>
    </div>
  </section>;
}
