'use client';

import { useEffect, useRef, useState } from 'react';
import { api, explain, stream } from '@/lib/api';
import type { ChatMessage } from '@/lib/types';
import { Check, Lightbulb, SendHorizontal, Sparkles, X } from 'lucide-react';
import Markdown from './markdown';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';

interface Ladder {
  ceiling?: number;
  turns_at_ceiling?: number;
  revealed?: boolean;
}

interface Props {
  scope: string;
  title: string;
  language?: string;
  /** Problem pages supply the current code and whether a Run/Submit happened since the last message. */
  context?: () => { code: string; newAttempt: boolean };
  onSent?: () => void;
  /** Opens the panel from outside (e.g. a "Get a hint" button). Increment to trigger. */
  openSignal?: number;
}

const LEVEL_TEXT = ['Asking what you tried', 'Guiding question', 'Conceptual nudge', 'Approach', 'Partial plan', 'Full walkthrough'];
const STARTERS: Record<string, string[]> = {
  general: ['What should I focus on this week?', 'Pick 3 problems for me', 'Where am I weakest right now?'],
  concept: ['Explain this with a real example', 'When would I use this?', 'Give me a problem to practise this'],
};

export default function Assistant({ scope, title, language, context, onSent, openSignal = 0 }: Props) {
  const problem = scope.startsWith('problem:');
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [ladder, setLadder] = useState<Ladder>({});
  const [loaded, setLoaded] = useState(false);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmReveal, setConfirmReveal] = useState(false);
  const [activity, setActivity] = useState<string[]>([]);
  const scroller = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);

  useEffect(() => { if (openSignal) setOpen(true); }, [openSignal]);
  useEffect(() => { setLoaded(false); setMessages([]); setLadder({}); }, [scope]);
  useEffect(() => {
    if (!open || loaded) return;
    api
      .get<{ messages: ChatMessage[]; ladder: Ladder }>(`/assistant/thread?scope=${encodeURIComponent(scope)}`)
      .then(t => { setMessages(t.messages); setLadder(t.ladder ?? {}); setLoaded(true); })
      .catch(e => setError(explain(e)));
  }, [open, loaded, scope]);
  useEffect(() => {
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [messages, open]);
  useEffect(() => {
    if (!open) return;
    input.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open]);

  async function send(intent: 'chat' | 'hint' | 'reveal_confirmed', text = draft) {
    if (busy) return;
    const message = text.trim();
    if (intent === 'chat' && !message) return;
    setBusy(true);
    setError('');
    setConfirmReveal(false);
    const extra = context?.() ?? { code: '', newAttempt: false };
    const shown = message || (intent === 'hint' ? "I'd like a hint." : 'Please walk me through the full solution.');
    setMessages(m => [...m, { role: 'user', content: shown }, { role: 'assistant', content: '' }]);
    setDraft('');
    setActivity([]);
    let reply = '';
    const update = (content: string, level?: number) =>
      setMessages(m => [...m.slice(0, -1), { role: 'assistant', content, level }]);
    try {
      for await (const { event, data } of stream('/assistant/messages', {
        scope, message, intent, code: extra.code, new_attempt: extra.newAttempt,
      })) {
        if (event === 'tool') setActivity(a => (a.includes(String(data.label)) ? a : [...a, String(data.label)]));
        else if (event === 'delta') { reply += String(data.text ?? ''); update(reply); }
        else if (event === 'replace') { reply = String(data.text ?? ''); update(reply); }
        else if (event === 'done') {
          reply = String(data.text ?? reply);
          update(reply, Number(data.level));
          if (problem) {
            const level = Number(data.level);
            setLadder(l => ({ ...l, ceiling: Math.max(l.ceiling ?? 0, Math.min(level, 4)), revealed: l.revealed || level >= 5 }));
          }
        }
      }
      onSent?.();
    } catch (e) {
      setMessages(m => m.slice(0, -2));
      setDraft(message);
      setError(explain(e));
    } finally {
      setBusy(false);
      setActivity([]);
    }
  }

  if (!open) {
    return (
      <div className="fixed right-4 bottom-20 z-50 md:right-6 md:bottom-6">
        <Button size="lg" className="h-11 rounded-full px-5 shadow-lg shadow-primary/25" onClick={() => setOpen(true)} aria-haspopup="dialog">
          <Sparkles data-icon="inline-start" /> {title}
        </Button>
      </div>
    );
  }

  const level = ladder.revealed ? 5 : ladder.ceiling ?? 0;
  return (
    <section
      className="fixed inset-x-2 bottom-2 z-[60] flex h-[calc(100dvh-5rem)] flex-col overflow-hidden rounded-2xl border bg-popover text-popover-foreground shadow-2xl animate-in fade-in slide-in-from-bottom-4 sm:inset-x-auto sm:right-6 sm:bottom-6 sm:h-[min(680px,calc(100dvh-6rem))] sm:w-[420px]"
      role="dialog"
      aria-label={title}
    >
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid size-8 flex-none place-items-center rounded-full bg-primary/12 text-primary"><Sparkles className="size-4" /></span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">{title}</h2>
            {problem ? (
              <div className="mt-1 flex items-center gap-2">
                <div className="flex gap-0.5" aria-hidden="true">
                  {[0, 1, 2, 3, 4, 5].map(n => <span key={n} className={`h-1 w-3 rounded-full ${n <= level ? 'bg-primary' : 'bg-muted'}`} />)}
                </div>
                <p className="text-xs text-muted-foreground">{LEVEL_TEXT[level]}</p>
              </div>
            ) : <p className="text-xs text-muted-foreground">Asks before it tells · knows your plan</p>}
          </div>
        </div>
        <Button variant="ghost" size="icon-sm" onClick={() => setOpen(false)} aria-label="Close tutor"><X /></Button>
      </header>
      <div ref={scroller} className="flex-1 space-y-3 overflow-y-auto px-4 py-4" aria-live="polite">
        {!messages.length ? (
          <div className="text-sm text-muted-foreground">
            {problem
              ? 'Stuck? Tell me what you tried and where it breaks. Hints get more specific as you keep working — run your code or explain your thinking to unlock the next level.'
              : scope === 'general'
                ? 'I know your plan, your progress and the whole practice library. Ask what to study, which problems to do next, or anything you are stuck on.'
                : 'Ask about this lesson, an idea that feels fuzzy, or what to focus on next.'}
            {!problem ? (
              <div className="mt-4 grid gap-2">
                {STARTERS[scope === 'general' ? 'general' : 'concept'].map(s => (
                  <Button key={s} type="button" variant="outline" size="sm" className="h-auto justify-start py-2 text-left font-normal whitespace-normal" disabled={busy || !loaded} onClick={() => send('chat', s)}>
                    {s}
                  </Button>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="chat-bubble-user">{m.content}</div>
          ) : (
            <div key={i} className="chat-bubble-assistant">
              {busy && i === messages.length - 1 && activity.length ? (
                <ul className="mb-2 grid gap-1 text-xs text-muted-foreground" aria-label="What the tutor is checking">
                  {activity.map((a, j) => (
                    <li key={a} className="flex items-center gap-2">
                      {j === activity.length - 1 && !m.content ? <Spinner className="size-3" /> : <Check className="size-3 text-success" />}
                      {a}
                    </li>
                  ))}
                </ul>
              ) : null}
              {m.content ? (
                <Markdown source={m.content} language={language} className="prose-compact" />
              ) : activity.length && busy && i === messages.length - 1 ? null : (
                <span className="flex items-center gap-1 py-1" aria-label="Thinking">
                  {[0, 1, 2].map(n => <span key={n} className="size-1.5 animate-bounce rounded-full bg-muted-foreground/60" style={{ animationDelay: `${n * 120}ms` }} />)}
                </span>
              )}
            </div>
          ),
        )}
      </div>
      {error ? <p role="alert" className="mx-4 mb-2 rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p> : null}
      {problem ? (
        <div className="flex flex-wrap items-center gap-2 border-t px-4 pt-3">
          <Button type="button" variant="secondary" size="sm" disabled={busy} onClick={() => send('hint')}><Lightbulb data-icon="inline-start" /> Give me a hint</Button>
          {confirmReveal ? (
            <span className="flex flex-wrap items-center gap-2 text-xs">
              Show the full solution? It counts as heavy help.
              <Button type="button" size="xs" variant="destructive" disabled={busy} onClick={() => send('reveal_confirmed', '')}>Yes, show it</Button>
              <Button type="button" size="xs" variant="ghost" onClick={() => setConfirmReveal(false)}>Keep trying</Button>
            </span>
          ) : (
            <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={() => setConfirmReveal(true)}>Show solution</Button>
          )}
        </div>
      ) : null}
      <form className="flex items-end gap-2 p-3" onSubmit={e => { e.preventDefault(); send('chat'); }}>
        <label className="sr-only" htmlFor={`assistant-${scope}`}>Message</label>
        <Textarea
          id={`assistant-${scope}`}
          ref={input}
          className="max-h-40 min-h-10 flex-1 resize-none"
          rows={2}
          maxLength={4000}
          value={draft}
          placeholder={problem ? 'What did you try? Where does it break?' : 'Ask a question…'}
          onChange={e => setDraft(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send('chat'); } }}
        />
        <Button size="icon-lg" disabled={busy || !draft.trim()} aria-label="Send"><SendHorizontal /></Button>
      </form>
    </section>
  );
}
