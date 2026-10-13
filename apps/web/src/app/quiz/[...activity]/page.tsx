'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, BookOpen, CheckCircle2, Clock, Heart, Lock, Trophy, Unlock, XCircle } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { KIND_LABEL, conceptHref, formatStamp, joinSegments } from '@/lib/routes';
import type { ActivityKind, Gate, QuizQuestion, QuizSession } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BackLink, ErrorNote, Loading, Ring } from '@/components/common';
import { Choice } from '@/components/choice';
import { celebrate } from '@/components/celebrate';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

function Options({ q, choice, onChoose, graded }: { q: QuizQuestion; choice: number | null; onChoose(i: number): void; graded: boolean }) {
  return (
    <div className="grid gap-2.5" role="radiogroup" aria-label="Answer choices">
      {q.options.map((option, index) => {
        let tone: 'idle' | 'correct' | 'wrong' = 'idle';
        if (graded && q.answered) {
          if (index === q.answer) tone = 'correct';
          else if (index === q.choice) tone = 'wrong';
        }
        const selected = q.answered ? q.choice === index : choice === index;
        return (
          <Choice
            key={index}
            role="radio"
            aria-checked={selected}
            selected={selected && tone === 'idle'}
            tone={tone}
            marker={String.fromCharCode(65 + index)}
            disabled={q.answered}
            onClick={() => onChoose(index)}
          >
            <span className="whitespace-pre-wrap">{option}</span>
          </Choice>
        );
      })}
    </div>
  );
}

/** One segment per question: green, red or pending — progress you can see at a glance. */
function Segments({ questions, index }: { questions: QuizQuestion[]; index: number }) {
  return (
    <div className="mb-8 flex gap-1" aria-hidden="true">
      {questions.map((q, i) => (
        <span
          key={q.id}
          className={cn(
            'h-1.5 flex-1 rounded-full bg-muted transition-colors',
            q.answered && q.correct === true && 'bg-success',
            q.answered && q.correct === false && 'bg-destructive',
            q.answered && q.correct === undefined && 'bg-primary',
            !q.answered && i === index && 'bg-primary/40',
          )}
        />
      ))}
    </div>
  );
}

/** Difficulty climbs with each correct answer; misses are limited. The stakes stay visible. */
function GateMeter({ gate, asked }: { gate: Gate; asked: number }) {
  const position = Math.max(0, gate.levels.indexOf(gate.level));
  const left = gate.max_strikes - gate.strikes;
  return (
    <Card size="sm" className="mb-8">
      <CardContent className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-center">
        <div className="min-w-0">
          <p className="flex items-center gap-2 text-sm font-medium"><Lock className="size-4 text-primary" /> Checkpoint · {gate.module}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            {gate.unlocks ? <>Pass to unlock <span className="font-medium text-foreground">{gate.unlocks}</span>. </> : null}
            Questions get harder each time you&apos;re right. Results at the end.
          </p>
          <div className="mt-3 flex items-end gap-1.5" role="img" aria-label={`Difficulty level ${position + 1} of ${gate.levels.length}`}>
            {gate.levels.map((level, i) => (
              <span
                key={level}
                className={cn('w-8 rounded-sm transition-all duration-500', i <= position ? 'bg-primary' : 'bg-muted')}
                style={{ height: `${10 + i * 8}px` }}
              />
            ))}
            <span className="ml-2 text-xs text-muted-foreground">Difficulty {position + 1}/{gate.levels.length}</span>
          </div>
        </div>
        <div className="flex items-center gap-5 text-sm">
          <div className="text-center">
            <p className="text-xs text-muted-foreground">Question</p>
            <p className="font-semibold tabular-nums">{asked} <span className="font-normal text-muted-foreground">/ up to {gate.max_items}</span></p>
          </div>
          <div className="text-center" aria-label={`${left} misses left`}>
            <p className="text-xs text-muted-foreground">Misses left</p>
            <p className="flex justify-center gap-0.5">
              {Array.from({ length: gate.max_strikes }, (_, i) => (
                <Heart key={i} className={cn('size-4', i < left ? 'fill-destructive text-destructive' : 'text-muted-foreground/40')} />
              ))}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function GateResult({ gate }: { gate: Gate }) {
  const percent = Math.round((gate.score ?? 0) * 100);
  if (gate.passed) {
    return (
      <Card className="mb-8 overflow-hidden border-0 bg-gradient-to-br from-success/15 via-card to-card ring-success/30 animate-in fade-in zoom-in-95 duration-500">
        <CardContent className="flex flex-wrap items-center gap-6 py-2">
          <span className="grid size-24 place-items-center rounded-full bg-success/15 text-success"><Unlock className="size-10" /></span>
          <div className="min-w-0 flex-1">
            <p className="text-sm text-muted-foreground">Checkpoint passed · {percent}% weighted score</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">{gate.unlocks ? `${gate.unlocks} unlocked` : 'Course checkpoint passed'}</h1>
            <p className="mt-2 text-muted-foreground">
              You held up as the questions got harder — {gate.hard_correct} right at the top level. Your plan now opens the next module.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card className="mb-8 animate-in fade-in zoom-in-95 duration-500">
      <CardContent className="flex flex-wrap items-center gap-6 py-2">
        <Ring value={percent} size={104} stroke={9} label={<span className="text-xl">{percent}%</span>} />
        <div className="min-w-0 flex-1">
          <p className="text-sm text-muted-foreground">Checkpoint · {gate.module}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">Not yet — and that&apos;s useful</h1>
          <p className="mt-2 text-muted-foreground">
            Passing needs {Math.round(gate.pass_score * 100)}% and {gate.hard_needed} right at the hardest level ({gate.hard_correct} this time).
            Your plan added focused reviews on the weakest topics.
          </p>
          {gate.retry_at ? (
            <p className="mt-3 inline-flex items-center gap-2 rounded-lg bg-muted px-3 py-1.5 text-sm">
              <Clock className="size-4 text-primary" /> Next attempt opens {formatStamp(gate.retry_at)}
            </p>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Quiz() {
  const allowed = useGuard('active');
  const params = useParams<{ activity: string[] }>();
  const activityId = joinSegments(params.activity);
  const kind = activityId.split(':')[0] as ActivityKind;
  const [session, setSession] = useState<QuizSession | null>(null);
  const [index, setIndex] = useState(0);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api
      .get<QuizSession>(`/quiz/${activityId}`)
      .then(s => {
        setSession(s);
        const first = s.questions.findIndex(q => !q.answered);
        setIndex(first < 0 ? 0 : first);
      })
      .catch(e => setError(explain(e)));
  }, [activityId]);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  async function answer() {
    if (!session || choice === null) return;
    const q = session.questions[index];
    setBusy(true);
    setError('');
    try {
      const next = await api.post<QuizSession>(`/quiz/${activityId}/answer`, { item: q.id, choice });
      setSession(next);
      setChoice(null);
      if (next.feedback === 'at_end' && !next.completed) setIndex(i => Math.min(i + 1, next.questions.length - 1));
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  const total = session?.questions.length ?? 0;
  const showResults = Boolean(session?.completed && (session.feedback === 'at_end' || index === total));
  const percent = Math.round((session?.score ?? 0) * 100);
  const gatePassed = session?.gate?.passed;
  useEffect(() => {
    if (!showResults) return;
    if (gatePassed) celebrate('big');
    else if (gatePassed === undefined && percent >= 80) celebrate(percent === 100 ? 'big' : 'small');
  }, [showResults, percent, gatePassed]);

  if (!allowed || (!session && !error)) return <Loading variant="quiz" />;
  if (!session) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const title = KIND_LABEL[kind] ?? 'Quiz';
  const topic = kind === 'checkpoint' ? 'Mixed questions from this module' : session.questions[0]?.concept_title;

  if (showResults) {
    const wrong = session.questions.filter(q => q.correct === false);
    const right = session.questions.filter(q => q.correct).length;
    return (
      <div className="mx-auto w-full max-w-3xl px-4 pt-6 pb-24 sm:px-6 md:pt-8">
        <BackLink href="/today">Today</BackLink>
        {session.gate ? <GateResult gate={session.gate} /> : (
        <Card className="mb-8 animate-in fade-in zoom-in-95 duration-500">
          <CardContent className="flex flex-wrap items-center gap-6 py-2">
            <Ring value={percent} size={104} stroke={9} tone={percent >= 80 ? 'success' : 'primary'} label={<span className="text-xl">{percent}%</span>} />
            <div className="min-w-0 flex-1">
              <p className="text-sm text-muted-foreground">{title} complete</p>
              <h1 className="mt-1 text-3xl font-semibold tracking-tight">
                {percent >= 80 ? 'Nicely done' : percent >= 50 ? 'Getting there' : "Let's shore this up"}
              </h1>
              <p className="mt-2 text-muted-foreground">
                {right} of {total} correct.{' '}
                {percent >= 80 ? 'Your plan moves you forward.' : 'Your plan adds a refresher and more practice where it helps.'}
              </p>
            </div>
          </CardContent>
        </Card>
        )}
        {wrong.length ? (
          <section className="mb-8">
            <h2 className="mb-3 text-lg font-semibold">Worth another look</h2>
            <div className="grid gap-4">
              {wrong.map(q => (
                <Card key={q.id}>
                  <CardContent className="grid gap-3">
                    <Badge variant="outline" className="w-fit">{q.concept_title}</Badge>
                    <p className="font-medium">{q.prompt}</p>
                    {q.code ? <pre className="code-block">{q.code}</pre> : null}
                    <p className="flex items-start gap-2 rounded-lg bg-success/10 p-3 text-sm">
                      <CheckCircle2 className="mt-0.5 size-4 flex-none text-success" />
                      <span><span className="font-semibold">Answer:</span> {q.answer !== undefined ? q.options[q.answer] : ''}</span>
                    </p>
                    {q.explanation ? <p className="text-sm text-muted-foreground">{q.explanation}</p> : null}
                    <Button asChild variant="link" className="h-auto w-fit p-0">
                      <Link href={conceptHref(q.concept)}><BookOpen data-icon="inline-start" /> Revisit the lesson</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </section>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <Button asChild size="lg" className="h-10 px-5">
            <Link href={session.gate?.passed ? '/plan' : '/today'}>
              {session.gate?.passed ? <><Trophy data-icon="inline-start" /> See what&apos;s unlocked</> : 'Continue'} <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
          <Button asChild size="lg" variant="outline" className="h-10"><Link href="/progress">See progress</Link></Button>
        </div>
      </div>
    );
  }

  const q = session.questions[Math.min(index, total - 1)];
  const graded = session.feedback === 'immediate';
  const isLast = index >= total - 1;
  return (
    <div className="mx-auto w-full max-w-3xl px-4 pt-6 pb-24 sm:px-6 md:pt-8">
      <BackLink href="/today">Today</BackLink>
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-3">
        <p className="text-sm font-medium">{title}{topic ? <span className="text-muted-foreground"> · {topic}</span> : null}</p>
        {session.gate ? null : <p className="text-sm text-muted-foreground tabular-nums">Question {Math.min(index + 1, total)} of {total}</p>}
      </div>
      {session.gate ? <GateMeter gate={session.gate} asked={Math.min(index + 1, total)} /> : <Segments questions={session.questions} index={index} />}

      <div key={q.id} className="grid gap-5 animate-in fade-in slide-in-from-right-4 duration-300">
        {kind === 'checkpoint' ? <Badge variant="outline" className="w-fit">{q.concept_title}</Badge> : null}
        <h1 className="text-xl font-semibold leading-snug tracking-tight md:text-2xl">{q.prompt}</h1>
        {q.code ? <pre className="code-block">{q.code}</pre> : null}
        <Options q={q} choice={choice} onChoose={setChoice} graded={graded} />

        {graded && q.answered ? (
          <div
            role="status"
            className={cn(
              'flex items-start gap-3 rounded-xl border p-4 animate-in fade-in slide-in-from-bottom-2',
              q.correct ? 'border-success/30 bg-success/10' : 'border-destructive/30 bg-destructive/8',
            )}
          >
            {q.correct ? <CheckCircle2 className="mt-0.5 size-5 flex-none text-success" /> : <XCircle className="mt-0.5 size-5 flex-none text-destructive" />}
            <div>
              <p className="font-semibold">{q.correct ? 'Correct' : 'Not quite'}</p>
              {q.explanation ? <p className="mt-1 text-sm text-muted-foreground">{q.explanation}</p> : null}
            </div>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-3">
          {!q.answered ? (
            <Button size="lg" className="h-10 px-5" disabled={busy || choice === null} onClick={answer}>Check answer</Button>
          ) : graded ? (
            <Button size="lg" className="h-10 px-5" onClick={() => setIndex(isLast ? total : index + 1)}>
              {isLast ? 'See results' : 'Next question'} <ArrowRight data-icon="inline-end" />
            </Button>
          ) : null}
        </div>
        {error ? <ErrorNote message={error} /> : null}
      </div>
    </div>
  );
}
