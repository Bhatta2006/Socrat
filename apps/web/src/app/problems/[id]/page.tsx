'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { AlertTriangle, CheckCircle2, ChevronDown, Clock, Cloud, CloudOff, Lightbulb, Loader2, Play, Send, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { LANGUAGE_LABEL, conceptHref, formatStamp } from '@/lib/routes';
import type { Case, Language, ProblemView, Submission } from '@/lib/types';
import { cn } from '@/lib/utils';
import CodeEditor from '@/components/code-editor';
import { parseDiagnostics } from '@/components/code-editor/diagnostics';
import Markdown from '@/components/markdown';
import Assistant from '@/components/assistant';
import { celebrate } from '@/components/celebrate';
import { BackLink, Difficulty, ErrorNote, Loading } from '@/components/common';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';

type Tone = 'success' | 'info' | 'error' | 'warning';
const VERDICT: Record<string, { label: string; tone: Tone }> = {
  accepted: { label: 'Accepted', tone: 'success' },
  ran: { label: 'Ran', tone: 'info' },
  executed: { label: 'Ran', tone: 'info' },
  wrong_answer: { label: 'Wrong answer', tone: 'error' },
  compile_error: { label: 'Compilation error', tone: 'error' },
  runtime_error: { label: 'Runtime error', tone: 'error' },
  timeout: { label: 'Time limit exceeded', tone: 'warning' },
  output_limit: { label: 'Output limit exceeded', tone: 'warning' },
  memory_limit: { label: 'Memory limit exceeded', tone: 'warning' },
  system_error: { label: 'Runner error — not your fault, try again', tone: 'warning' },
};
const TONE_CLASS: Record<Tone, string> = {
  success: 'border-success/30 bg-success/10 text-success',
  info: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  error: 'border-destructive/30 bg-destructive/10 text-destructive',
  warning: 'border-warning/40 bg-warning/15 text-warning-foreground dark:text-warning',
};
const TONE_ICON: Record<Tone, typeof CheckCircle2> = { success: CheckCircle2, info: Play, error: XCircle, warning: AlertTriangle };
const CASE_LABEL: Record<string, string> = {
  passed: 'Passed', wrong_answer: 'Wrong answer', runtime_error: 'Runtime error', timeout: 'Too slow',
  output_limit: 'Too much output', memory_limit: 'Too much memory', compile_error: 'Did not compile', executed: 'Ran', not_run: 'Not run',
};

function CaseDetail({ c, index }: { c: Case; index: number }) {
  const ok = c.status === 'passed' || c.status === 'executed';
  return (
    <Collapsible defaultOpen={!ok && index < 3} className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-3 py-2 text-sm">
        <span className="flex items-center gap-2">
          {ok ? <CheckCircle2 className="size-4 text-success" /> : <XCircle className="size-4 text-destructive" />}
          {c.expected === null ? 'Your custom input' : `Example ${index + 1}`}
        </span>
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {CASE_LABEL[c.status] ?? c.status}{c.wall_ms ? ` · ${c.wall_ms} ms` : ''}
          <ChevronDown className="size-3.5 transition-transform group-data-[state=open]:rotate-180" />
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-2 border-t p-3 text-xs">
          {c.input !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Input</p><pre className="io-block">{c.input}</pre></div> : null}
          {c.expected !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Expected</p><pre className="io-block">{c.expected}</pre></div> : null}
          {c.stdout !== null ? <div><p className="mb-1 font-medium text-muted-foreground">Your output</p><pre className="io-block">{c.stdout || '(no output)'}</pre></div> : null}
          {c.stderr ? <div><p className="mb-1 font-medium text-muted-foreground">Errors</p><pre className="io-block">{c.stderr}</pre></div> : null}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

function HiddenSummary({ cases }: { cases: Case[] }) {
  const hidden = cases.map((c, index) => ({ c, index })).filter(({ c }) => !c.public);
  if (!hidden.length) return null;
  const failed = hidden.filter(({ c }) => c.status !== 'passed');
  const slowest = Math.max(...hidden.map(({ c }) => c.wall_ms || 0));
  return (
    <Collapsible defaultOpen={failed.length > 0} className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-3 py-2 text-sm">
        <span className="flex items-center gap-2">
          {failed.length ? <XCircle className="size-4 text-destructive" /> : <CheckCircle2 className="size-4 text-success" />}
          Hidden tests
        </span>
        <span className="flex items-center gap-2 text-xs text-muted-foreground">
          {hidden.length - failed.length} of {hidden.length} passed{slowest ? ` · slowest ${slowest} ms` : ''}
          <ChevronDown className="size-3.5 transition-transform group-data-[state=open]:rotate-180" />
        </span>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="grid gap-1 border-t p-3 text-xs">
          {failed.length ? (
            failed.map(({ c, index }) => (
              <div key={index}>
                <p className="flex justify-between gap-2"><span>Hidden test {index + 1}</span><span className="font-medium">{CASE_LABEL[c.status] ?? c.status}</span></p>
                {c.stderr ? <pre className="io-block mt-1">{c.stderr}</pre> : null}
              </div>
            ))
          ) : (
            <p className="text-muted-foreground">All passed.</p>
          )}
          <p className="mt-1 text-muted-foreground">Hidden tests check edge cases and performance; their data stays private.</p>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

export default function Problem() {
  const allowed = useGuard('signed-in');
  const { profile, features } = useSession();
  const { resolvedTheme } = useTheme();
  const params = useParams<{ id: string }>();
  const problemId = params.id;
  const [language, setLanguage] = useState<Language | null>(null);
  const [problem, setProblem] = useState<ProblemView | null>(null);
  const [source, setSource] = useState('');
  const [runtimes, setRuntimes] = useState<Record<string, boolean>>({});
  const [result, setResult] = useState<Submission | null>(null);
  const [pending, setPending] = useState<'run' | 'submit' | null>(null);
  const [customInput, setCustomInput] = useState('');
  const [useCustom, setUseCustom] = useState(false);
  const [saved, setSaved] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [error, setError] = useState('');
  const [hintSignal, setHintSignal] = useState(0);
  const attempted = useRef(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const latest = useRef({ source: '', language: null as Language | null });
  latest.current = { source, language };

  const lang = language ?? profile?.enrollment?.language ?? 'python';

  const load = useCallback(() => {
    setError('');
    api
      .get<ProblemView>(`/problems/${problemId}?language=${lang}`)
      .then(p => { setProblem(p); setSource(p.draft ?? p.starter); setSaved('saved'); })
      .catch(e => setError(explain(e)));
  }, [problemId, lang]);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  useEffect(() => {
    if (!allowed) return;
    api.get<{ languages: Record<string, boolean> }>('/runtimes').then(r => setRuntimes(r.languages)).catch(() => undefined);
  }, [allowed]);

  const saveDraft = useCallback(async () => {
    const { source: text, language: l } = latest.current;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setSaved('saving');
    try {
      await api.put(`/problems/${problemId}/draft`, { source: text, language: l ?? lang });
      setSaved('saved');
    } catch {
      setSaved('unsaved');
    }
  }, [problemId, lang]);

  function onChange(next: string) {
    setSource(next);
    setSaved('unsaved');
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(saveDraft, 1500);
  }
  useEffect(() => () => { if (saveTimer.current) clearTimeout(saveTimer.current); }, []);

  async function execute(mode: 'run' | 'submit') {
    if (pending) return;
    if (saveTimer.current) clearTimeout(saveTimer.current);
    setPending(mode);
    setError('');
    setResult(null);
    try {
      const body: Record<string, unknown> = { source, language: lang };
      if (mode === 'run' && useCustom) body.custom_input = customInput;
      let job = await api.post<Submission>(`/problems/${problemId}/${mode}`, body);
      setSaved('saved');
      attempted.current = true;
      const started = Date.now();
      while (job.status !== 'done' && Date.now() - started < 90_000) {
        await new Promise(r => setTimeout(r, job.status === 'queued' ? 600 : 400));
        job = await api.get<Submission>(`/submissions/${job.id}`);
        setResult(job);
      }
      setResult(job);
      if (job.status !== 'done') setError('The runner is taking longer than usual. Your submission is saved; check back in a moment.');
      if (mode === 'submit' && job.verdict === 'accepted') {
        setProblem(p => (p ? { ...p, solved: true } : p));
        celebrate('big');
        toast.success('Accepted!', { description: 'Every test passed. Your mastery just went up.' });
      }
      if (job.status === 'done') {
        setProblem(p => p && { ...p, history: [{ id: job.id, mode: job.mode, verdict: job.verdict, status: job.status, passed: job.passed, total: job.total, at: job.created_at }, ...p.history].slice(0, 10) });
      }
    } catch (e) {
      setError(explain(e));
    } finally {
      setPending(null);
    }
  }

  const diagnostics = useMemo(() => {
    if (!result?.cases?.length) return [];
    const text = result.cases.map(c => c.stderr ?? '').filter(Boolean).join('\n');
    return parseDiagnostics(text);
  }, [result]);

  if (!allowed || (!problem && !error)) return <Loading />;
  if (!problem) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const runtimeKnown = Object.keys(runtimes).length > 0;
  const runtimeReady = !runtimeKnown || runtimes[lang];
  const canExecute = Boolean(features?.code_execution) && runtimeReady;
  const verdict = result?.status === 'done' ? VERDICT[result.verdict] ?? { label: result.verdict, tone: 'info' as Tone } : null;
  const VerdictIcon = verdict ? TONE_ICON[verdict.tone] : CheckCircle2;

  return (
    <div className="mx-auto w-full max-w-[1440px] px-4 pt-6 pb-28 sm:px-6 md:pb-10">
      <BackLink href="/today">Today</BackLink>
      <div className="workspace">
        <Card className="min-w-0 gap-0 py-0" aria-labelledby="problem-title">
          <Tabs defaultValue="description" className="gap-0">
            <div className="border-b px-4 pt-3">
              <TabsList variant="line">
                <TabsTrigger value="description">Description</TabsTrigger>
                <TabsTrigger value="attempts">Attempts{problem.history.length ? ` (${problem.history.length})` : ''}</TabsTrigger>
              </TabsList>
            </div>
            <TabsContent value="description" className="max-h-none overflow-y-auto p-5 lg:max-h-[calc(100dvh-11rem)]">
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <Difficulty level={problem.difficulty} />
                <Badge asChild variant="secondary"><Link href={conceptHref(problem.concept.id)}>{problem.concept.title}</Link></Badge>
                {problem.solved ? <Badge variant="outline" className="gap-1 border-success/30 bg-success/10 text-success"><CheckCircle2 className="size-3" /> Solved</Badge> : null}
              </div>
              <h1 id="problem-title" className="mb-5 text-2xl font-semibold tracking-tight">{problem.title}</h1>
              <Markdown source={problem.statement} language={lang} className="prose-compact" />
              <h2 className="mt-6 mb-1 text-sm font-semibold">Input</h2>
              <Markdown source={problem.input_format} className="prose-compact" />
              <h2 className="mt-4 mb-1 text-sm font-semibold">Output</h2>
              <Markdown source={problem.output_format} className="prose-compact" />
              {problem.constraints.length ? (
                <>
                  <h2 className="mt-4 mb-1 text-sm font-semibold">Constraints</h2>
                  <ul className="list-disc pl-5 text-sm text-muted-foreground">{problem.constraints.map(c => <li key={c} className="font-mono text-xs">{c}</li>)}</ul>
                </>
              ) : null}
              {problem.examples.map((ex, i) => (
                <div key={i} className="mt-5">
                  <h2 className="mb-2 text-sm font-semibold">Example {i + 1}</h2>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <div><p className="mb-1 text-xs text-muted-foreground">Input</p><pre className="io-block">{ex.input}</pre></div>
                    <div><p className="mb-1 text-xs text-muted-foreground">Output</p><pre className="io-block">{ex.output}</pre></div>
                  </div>
                  {ex.explanation ? <p className="mt-2 text-sm text-muted-foreground">{ex.explanation}</p> : null}
                </div>
              ))}
            </TabsContent>
            <TabsContent value="attempts" className="p-5">
              {problem.history.length ? (
                <ul className="grid divide-y text-sm">
                  {problem.history.map(h => {
                    const v = VERDICT[h.verdict];
                    return (
                      <li key={h.id} className="flex items-center justify-between gap-2 py-2.5">
                        <span className="flex items-center gap-2">
                          <Badge variant="outline" className={cn(v ? TONE_CLASS[v.tone] : '')}>{v?.label ?? h.status}</Badge>
                          <span className="text-muted-foreground">{h.mode === 'submit' ? 'Submit' : 'Run'}</span>
                        </span>
                        <span className="text-xs text-muted-foreground tabular-nums">{h.passed}/{h.total} · {formatStamp(h.at)}</span>
                      </li>
                    );
                  })}
                </ul>
              ) : <p className="text-sm text-muted-foreground">No attempts yet. Run your code to test it on the examples.</p>}
            </TabsContent>
          </Tabs>
        </Card>

        <section className="grid min-w-0 gap-3" aria-label="Code workspace">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <label className="flex items-center gap-2 text-sm">
              <span className="sr-only">Language</span>
              <NativeSelect
                size="sm"
                value={lang}
                onChange={async e => { if (saved !== 'saved') await saveDraft(); setResult(null); setLanguage(e.target.value as Language); }}
              >
                {(['python', 'cpp', 'java'] as const).map(l => (
                  <NativeSelectOption key={l} value={l}>{LANGUAGE_LABEL[l]}{runtimeKnown && !runtimes[l] ? ' (runner offline)' : ''}</NativeSelectOption>
                ))}
              </NativeSelect>
            </label>
            <span className="flex items-center gap-1.5 text-xs text-muted-foreground" aria-live="polite">
              {saved === 'saving' ? <Loader2 className="size-3.5 animate-spin" /> : saved === 'saved' ? <Cloud className="size-3.5" /> : <CloudOff className="size-3.5" />}
              {saved === 'saving' ? 'Saving…' : saved === 'saved' ? 'Draft saved' : 'Unsaved changes'}
            </span>
          </div>
          <CodeEditor
            key={lang}
            language={lang}
            value={source}
            onChange={onChange}
            onBlur={() => { if (saved === 'unsaved') saveDraft(); }}
            fontSize={14}
            theme={resolvedTheme === 'dark' ? 'dark' : 'light'}
            diagnostics={diagnostics}
            ariaLabel={`${LANGUAGE_LABEL[lang]} solution editor`}
            assistMode="learning"
          />
          <p id="editor-keyboard-help" className="sr-only">Press Escape, then Tab, to move focus out of the editor.</p>

          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" size="lg" className="h-9" disabled={!canExecute || Boolean(pending)} onClick={() => execute('run')}>
              {pending === 'run' ? <Loader2 className="animate-spin" /> : <Play />} Run
            </Button>
            <Button size="lg" className="h-9 px-4" disabled={!canExecute || Boolean(pending)} onClick={() => execute('submit')}>
              {pending === 'submit' ? <Loader2 className="animate-spin" /> : <Send />} Submit
            </Button>
            <Button variant="ghost" size="lg" className="h-9" onClick={() => setHintSignal(n => n + 1)}><Lightbulb /> Stuck? Ask for a hint</Button>
            <label className="ml-auto flex items-center gap-2 text-sm">
              <Switch checked={useCustom} onCheckedChange={setUseCustom} />
              Custom input
            </label>
          </div>
          {useCustom ? (
            <Textarea className="font-mono text-sm" rows={4} value={customInput} onChange={e => setCustomInput(e.target.value)} maxLength={20000} aria-label="Custom input" placeholder="Input to feed your program when you press Run" />
          ) : null}
          {!features?.code_execution ? (
            <Alert><AlertDescription>Code execution is turned off on this server. Your drafts still save, and the tutor can review your code.</AlertDescription></Alert>
          ) : !runtimeReady ? (
            <Alert className="border-warning/40 bg-warning/10"><AlertTriangle /><AlertDescription>The {LANGUAGE_LABEL[lang]} runner is offline. Start the execution worker, or switch language.</AlertDescription></Alert>
          ) : null}
          {features?.execution_backend === 'local_process' ? (
            <p className="text-xs text-muted-foreground">Local dev sandbox — not secure for untrusted code.</p>
          ) : null}

          <div aria-live="polite">
            {pending && result?.status !== 'done' ? (
              <p className="flex items-center gap-2 rounded-lg border bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
                <Clock className="size-4 animate-pulse" /> {result?.status === 'running' ? 'Running your code…' : 'Waiting for a runner…'}
              </p>
            ) : null}
            {verdict && result ? (
              <div className="grid gap-3 animate-in fade-in slide-in-from-bottom-2">
                <div className={cn('flex flex-wrap items-center justify-between gap-2 rounded-xl border px-4 py-3', TONE_CLASS[verdict.tone])}>
                  <span className="flex items-center gap-2 font-semibold"><VerdictIcon className="size-5" />{result.mode === 'submit' ? 'Submission: ' : 'Run: '}{verdict.label}</span>
                  {result.total && result.verdict !== 'ran' ? <span className="text-sm tabular-nums">{result.passed} / {result.total} tests passed</span> : null}
                </div>
                {result.mode === 'submit' && result.verdict === 'accepted' ? (
                  <p className="text-sm">
                    {result.assistance >= 5 ? 'Solved with the full walkthrough — try rewriting it from memory tomorrow to make it stick. ' : result.assistance ? 'Solved with some hints — nice persistence. ' : 'Solved independently — excellent. '}
                    <Link href="/today" className="font-medium text-primary underline underline-offset-2">Back to today</Link>
                  </p>
                ) : null}
                <div className="grid gap-2">
                  {result.cases.map((c, i) => (c.public ? <CaseDetail key={i} c={c} index={i} /> : null))}
                  <HiddenSummary cases={result.cases} />
                </div>
              </div>
            ) : null}
          </div>
          {error ? <ErrorNote message={error} /> : null}
        </section>
      </div>
      <Assistant
        scope={`problem:${problem.id}`}
        title="Socratic tutor"
        language={lang}
        openSignal={hintSignal}
        context={() => ({ code: latest.current.source, newAttempt: attempted.current })}
        onSent={() => { attempted.current = false; }}
      />
    </div>
  );
}
