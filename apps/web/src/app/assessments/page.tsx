'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ArrowRight,
  BookOpen,
  CalendarCheck,
  CheckCircle2,
  ChevronDown,
  Clock,
  Code2,
  Lock,
  Sparkles,
  Target,
  Timer,
  TrendingDown,
  TrendingUp,
  XCircle,
} from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { conceptHref, formatStamp } from '@/lib/routes';
import type { AssessmentStatus, AssessmentView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BandBadge, ErrorNote, Loading, Page, PageHeader, Reveal, Ring } from '@/components/common';
import { Choice } from '@/components/choice';
import { celebrate } from '@/components/celebrate';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { Progress } from '@/components/ui/progress';
import { Spinner } from '@/components/ui/spinner';

interface Overview {
  current: AssessmentStatus;
  history: { id: string; week: string; score: number | null; finished_at: number }[];
}

function Countdown({ seconds, onExpire }: { seconds: number; onExpire: () => void }) {
  const [left, setLeft] = useState(seconds);
  useEffect(() => {
    setLeft(seconds);
    const started = Date.now();
    const timer = setInterval(() => {
      const next = Math.max(0, seconds - Math.floor((Date.now() - started) / 1000));
      setLeft(next);
      if (next === 0) {
        clearInterval(timer);
        onExpire();
      }
    }, 1000);
    return () => clearInterval(timer);
  }, [seconds, onExpire]);
  const minutes = Math.floor(left / 60);
  const secs = String(left % 60).padStart(2, '0');
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-semibold tabular-nums', left < 300 ? 'border-destructive/40 bg-destructive/10 text-destructive' : 'bg-muted')} role="timer" aria-label={`${minutes} minutes ${secs} seconds left`}>
      <Timer className="size-4" /> {minutes}:{secs}
    </span>
  );
}

function Locked({ status }: { status: AssessmentStatus }) {
  const remaining = Math.max(0, status.needed - status.topics.length);
  return (
    <Card>
      <CardContent className="py-6">
        <Empty className="border-0 p-0">
          <EmptyHeader>
            <EmptyMedia variant="icon"><Lock /></EmptyMedia>
            <EmptyTitle>Your weekly assessment unlocks as you study</EmptyTitle>
            <EmptyDescription>
              Study {remaining} more topic{remaining === 1 ? '' : 's'} this week and it opens — built only from what you learned, so it&apos;s yours alone.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Progress value={(100 * status.topics.length) / status.needed} className="h-2 w-56" aria-label="Topics studied this week" />
            {status.topics.length ? <p className="text-xs text-muted-foreground">So far: {status.topics.join(', ')}</p> : null}
            <Button asChild><Link href="/today">Continue today&apos;s plan <ArrowRight data-icon="inline-end" /></Link></Button>
          </EmptyContent>
        </Empty>
      </CardContent>
    </Card>
  );
}

function Available({ status, onStart, busy }: { status: AssessmentStatus; onStart: (timed: boolean) => void; busy: boolean }) {
  return (
    <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-primary/12 via-card to-card ring-primary/20">
      <div className="bg-grid pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_left,black,transparent_60%)]" aria-hidden="true" />
      <CardContent className="relative grid gap-5 py-2">
        <div>
          <Badge variant="secondary" className="mb-3 gap-1.5 bg-background/70"><Sparkles className="size-3" /> Ready · week {status.week.split('-W')[1]}</Badge>
          <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">Your week in {status.questions} questions</h2>
          <p className="mt-2 max-w-2xl text-muted-foreground">
            Picked from what you studied in the last seven days, weighted toward what&apos;s still shaky, plus a coding task.
            Answers are revealed at the end, and your tutor steps back until you submit.
          </p>
        </div>
        <ul className="flex flex-wrap gap-1.5">
          {status.topics.map(t => <li key={t}><Badge variant="outline" className="bg-background/60">{t}</Badge></li>)}
        </ul>
        <div className="flex flex-wrap gap-3">
          <Button size="lg" className="h-10 px-5 shadow-sm shadow-primary/20" disabled={busy} onClick={() => onStart(false)}>
            {busy ? <Spinner /> : <CalendarCheck data-icon="inline-start" />} Start assessment
          </Button>
          <Button size="lg" variant="outline" className="h-10" disabled={busy} onClick={() => onStart(true)}>
            <Timer data-icon="inline-start" /> Exam mode · {status.time_limit_minutes} min
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Attempt({ view, setView }: { view: AssessmentView; setView: (v: AssessmentView) => void }) {
  const firstOpen = view.questions.findIndex(q => !q.answered);
  const [index, setIndex] = useState(firstOpen < 0 ? 0 : firstOpen);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const answered = view.questions.filter(q => q.answered).length;
  const total = view.questions.length;
  const q = view.questions[Math.min(index, total - 1)];

  const finish = useCallback(async () => {
    setBusy(true);
    try {
      setView(await api.post<AssessmentView>(`/assessments/${view.id}/finish`));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }, [view.id, setView]);
  const expire = useCallback(() => { api.get<AssessmentView>(`/assessments/${view.id}`).then(setView).catch(() => undefined); }, [view.id, setView]);

  async function submit() {
    if (choice === null) return;
    setBusy(true);
    setError('');
    try {
      const next = await api.post<AssessmentView>(`/assessments/${view.id}/answer`, { item: q.id, choice });
      setChoice(null);
      setView(next);
      const following = next.questions.findIndex((x, i) => i > index && !x.answered);
      const anyOpen = next.questions.findIndex(x => !x.answered);
      setIndex(following >= 0 ? following : anyOpen >= 0 ? anyOpen : index);
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_300px]">
      <div className="min-w-0">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground tabular-nums">Question {Math.min(index + 1, total)} of {total} · {answered} answered</p>
          {view.timed && view.seconds_left !== null ? <Countdown seconds={view.seconds_left} onExpire={expire} /> : null}
        </div>
        <div className="mb-8 flex gap-1" aria-hidden="true">
          {view.questions.map((x, i) => (
            <button
              key={x.id}
              type="button"
              tabIndex={-1}
              onClick={() => { setIndex(i); setChoice(null); }}
              className={cn('h-1.5 flex-1 rounded-full transition-colors', x.answered ? 'bg-primary' : i === index ? 'bg-primary/40' : 'bg-muted')}
            />
          ))}
        </div>
        {q ? (
          <div key={q.id} className="grid gap-5 animate-in fade-in slide-in-from-right-4 duration-300">
            <Badge variant="outline" className="w-fit">{q.concept_title}</Badge>
            <h2 className="text-xl font-semibold leading-snug tracking-tight md:text-2xl">{q.prompt}</h2>
            {q.code ? <pre className="code-block">{q.code}</pre> : null}
            <div className="grid gap-2.5" role="radiogroup" aria-label="Answer choices">
              {q.options.map((option, i) => {
                const selected = q.answered ? q.choice === i : choice === i;
                return (
                  <Choice key={i} role="radio" aria-checked={selected} selected={selected} marker={String.fromCharCode(65 + i)} disabled={q.answered} onClick={() => setChoice(i)}>
                    <span className="whitespace-pre-wrap">{option}</span>
                  </Choice>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-3">
              {!q.answered ? (
                <Button size="lg" className="h-10 px-5" disabled={busy || choice === null} onClick={submit}>Save answer</Button>
              ) : (
                <p className="flex items-center gap-2 text-sm text-muted-foreground"><CheckCircle2 className="size-4 text-primary" /> Answer saved</p>
              )}
            </div>
          </div>
        ) : null}
        {error ? <ErrorNote message={error} /> : null}
      </div>

      <aside className="grid content-start gap-4 lg:sticky lg:top-20 lg:self-start">
        {view.coding.length ? (
          <Card size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Code2 className="size-4 text-primary" /> Coding tasks</CardTitle>
              <CardDescription>Solve and Submit in the editor; they count if accepted before you finish.</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="grid gap-2">
                {view.coding.map(c => (
                  <li key={c.id} className="flex items-center justify-between gap-2 text-sm">
                    <Link href={`/problems/${c.id}`} className="font-medium hover:text-primary hover:underline">{c.title}</Link>
                    {c.solved ? <CheckCircle2 className="size-4 text-success" aria-label="Solved" /> : <span className="text-xs text-muted-foreground">{c.concept}</span>}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ) : null}
        <Card size="sm">
          <CardContent className="grid gap-3">
            <p className="text-sm text-muted-foreground">{answered === total ? 'All questions answered.' : `${total - answered} question${total - answered === 1 ? '' : 's'} left.`} You can submit any time.</p>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button disabled={busy}>Submit assessment</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Submit your assessment?</AlertDialogTitle>
                  <AlertDialogDescription>
                    {answered < total ? `${total - answered} unanswered question${total - answered === 1 ? '' : 's'} will count as incorrect. ` : ''}
                    You&apos;ll see every answer and a report straight away.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep going</AlertDialogCancel>
                  <AlertDialogAction onClick={finish}>Submit</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </CardContent>
        </Card>
      </aside>
    </div>
  );
}

function Report({ view }: { view: AssessmentView }) {
  const report = view.report!;
  const percent = Math.round((view.score ?? 0) * 100);
  const delta = report.previous_score !== null ? percent - Math.round(report.previous_score * 100) : null;
  useEffect(() => { if (percent >= 80) celebrate('small'); }, [percent]);
  return (
    <div className="grid gap-6">
      <Reveal>
        <Card>
          <CardContent className="flex flex-wrap items-center gap-6 py-2">
            <Ring value={percent} size={112} stroke={9} tone={percent >= 80 ? 'success' : 'primary'} label={<span className="text-2xl">{percent}%</span>} />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-muted-foreground">Week {view.week.split('-W')[1]} · {report.minutes} min</p>
              <h2 className="mt-1 text-3xl font-semibold tracking-tight">
                {percent >= 80 ? 'A strong week' : percent >= 60 ? 'Solid progress' : 'A clear picture of what to work on'}
              </h2>
              <p className="mt-2 text-muted-foreground">
                {report.correct} of {report.questions} questions{report.coding_total ? ` · ${report.coding_solved} of ${report.coding_total} coding tasks` : ''}.
              </p>
              {delta !== null ? (
                <p className={cn('mt-2 inline-flex items-center gap-1.5 text-sm font-medium', delta >= 0 ? 'text-success' : 'text-destructive')}>
                  {delta >= 0 ? <TrendingUp className="size-4" /> : <TrendingDown className="size-4" />}
                  {delta >= 0 ? '+' : ''}{delta} points vs last week
                </p>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </Reveal>

      <div className="grid gap-6 lg:grid-cols-2">
        <Reveal index={1}>
          <Card className="h-full">
            <CardHeader><CardTitle>By topic</CardTitle><CardDescription>Mastery before → after this assessment</CardDescription></CardHeader>
            <CardContent>
              <ul className="grid gap-4">
                {report.topics.map(t => (
                  <li key={t.id}>
                    <div className="mb-1 flex items-center justify-between gap-2 text-sm">
                      <Link href={conceptHref(t.id)} className="font-medium hover:text-primary hover:underline">{t.title}</Link>
                      <span className="tabular-nums text-muted-foreground">{t.correct}/{t.total}</span>
                    </div>
                    <Progress value={(100 * t.correct) / t.total} className="h-1.5" aria-label={`${t.title}: ${t.correct} of ${t.total}`} />
                    <div className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                      <BandBadge band={t.band} />
                      <span className="tabular-nums">{Math.round(t.before * 100)}% → <span className="font-medium text-foreground">{Math.round(t.after * 100)}%</span></span>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </Reveal>
        <Reveal index={2}>
          <div className="grid gap-6">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Target className="size-4 text-primary" /> Focus next week</CardTitle></CardHeader>
              <CardContent>
                {report.focus.length ? (
                  <ul className="grid gap-2">
                    {report.focus.map(f => (
                      <li key={f.id}>
                        <Button asChild variant="outline" size="sm" className="w-full justify-between"><Link href={conceptHref(f.id)}>{f.title} <BookOpen /></Link></Button>
                      </li>
                    ))}
                  </ul>
                ) : <p className="text-sm text-muted-foreground">Nothing urgent — your plan will keep stretching you.</p>}
              </CardContent>
            </Card>
            {report.strengths.length ? (
              <Card>
                <CardHeader><CardTitle className="flex items-center gap-2"><CheckCircle2 className="size-4 text-success" /> Strengths</CardTitle></CardHeader>
                <CardContent className="flex flex-wrap gap-1.5">
                  {report.strengths.map(s => <Badge key={s} variant="outline" className="border-success/30 bg-success/10">{s}</Badge>)}
                </CardContent>
              </Card>
            ) : null}
          </div>
        </Reveal>
      </div>

      <Reveal index={3}>
        <Collapsible className="rounded-xl border bg-card">
          <CollapsibleTrigger className="group flex w-full items-center justify-between px-5 py-4 text-left font-medium">
            Review every question
            <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul className="grid gap-4 border-t p-5">
              {view.questions.map(q => (
                <li key={q.id} className="grid gap-2">
                  <p className="flex items-start gap-2 font-medium">
                    {q.correct ? <CheckCircle2 className="mt-0.5 size-4 flex-none text-success" /> : <XCircle className="mt-0.5 size-4 flex-none text-destructive" />}
                    {q.prompt}
                  </p>
                  {q.code ? <pre className="code-block">{q.code}</pre> : null}
                  <p className="text-sm"><span className="font-medium">Answer:</span> {q.answer !== undefined ? q.options[q.answer] : ''}</p>
                  {q.explanation ? <p className="text-sm text-muted-foreground">{q.explanation}</p> : null}
                </li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      </Reveal>
    </div>
  );
}

export default function Assessments() {
  const allowed = useGuard('active');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [view, setView] = useState<AssessmentView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<Overview>('/assessments')
      .then(async o => {
        setOverview(o);
        if (o.current.id) setView(await api.get<AssessmentView>(`/assessments/${o.current.id}`));
      })
      .catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  async function start(timed: boolean) {
    setBusy(true);
    setError('');
    try {
      setView(await api.post<AssessmentView>('/assessments/start', { timed }));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const history = useMemo(() => (overview?.history ?? []).slice().reverse(), [overview]);
  if (!allowed || (!overview && !error)) return <Loading />;
  if (!overview) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page>
      <PageHeader
        eyebrow="Weekly assessment"
        title={view?.finished ? 'Your week, measured' : 'Check what stuck this week'}
        description="Every week, a short assessment built from what you studied — never the same as anyone else's."
      />
      {view && !view.finished ? <Attempt view={view} setView={setView} /> : view?.finished ? <Report view={view} /> : overview.current.state === 'available' ? (
        <Available status={overview.current} onStart={start} busy={busy} />
      ) : <Locked status={overview.current} />}
      {error ? <ErrorNote message={error} /> : null}

      {history.length ? (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2"><Clock className="size-4 text-primary" /> Past weeks</CardTitle>
            <CardAction><span className="text-xs text-muted-foreground">{history.length} completed</span></CardAction>
          </CardHeader>
          <CardContent>
            <div className="flex h-28 items-end gap-2" role="img" aria-label="Weekly assessment scores over time">
              {history.map(h => {
                const pct = Math.round((h.score ?? 0) * 100);
                return (
                  <div key={h.id} className="flex flex-1 flex-col items-center gap-1" title={`Week ${h.week.split('-W')[1]}: ${pct}% · ${formatStamp(h.finished_at)}`}>
                    <span className="text-[10px] tabular-nums text-muted-foreground">{pct}</span>
                    <span className="w-full max-w-10 rounded-t-md bg-primary/80" style={{ height: `${Math.max(6, pct * 0.8)}px` }} />
                    <span className="text-[10px] text-muted-foreground">W{h.week.split('-W')[1]}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      ) : null}
    </Page>
  );
}
