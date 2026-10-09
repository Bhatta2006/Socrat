'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, Compass, Sparkles } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import type { PlacementQuestion, PlacementSummary } from '@/lib/types';
import { ErrorNote, Loading, Ring } from '@/components/common';
import { Choice } from '@/components/choice';
import { celebrate } from '@/components/celebrate';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

export default function Placement() {
  const allowed = useGuard('enrolled');
  const { refresh } = useSession();
  const [state, setState] = useState<PlacementQuestion | null>(null);
  const [summary, setSummary] = useState<PlacementSummary | null>(null);
  const [choice, setChoice] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const finish = useCallback(async () => {
    setSummary(await api.get<PlacementSummary>('/placement/summary'));
    await refresh();
    celebrate('small');
  }, [refresh]);

  useEffect(() => {
    if (!allowed) return;
    api
      .get<PlacementQuestion>('/placement')
      .then(async q => {
        setState(q);
        if (q.done) await finish();
      })
      .catch(e => setError(explain(e)));
  }, [allowed, finish]);

  async function submit(answer: number | null) {
    if (!state?.question) return;
    setBusy(true);
    setError('');
    try {
      const next = await api.post<PlacementQuestion>('/placement/answer', { item: state.question.id, choice: answer });
      setState(next);
      setChoice(null);
      if (next.done) await finish();
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  if (!allowed || (!state && !error)) return <Loading />;

  if (summary) {
    const percent = summary.asked ? Math.round((100 * summary.correct) / summary.asked) : 0;
    return (
      <div className="mx-auto w-full max-w-2xl px-4 pt-10 pb-24 sm:px-6 md:pt-16">
        <div className="animate-in fade-in zoom-in-95 duration-500">
          <div className="mb-8 flex flex-wrap items-center gap-6">
            <Ring value={percent} size={96} stroke={8} label={<span className="text-lg">{summary.correct}/{summary.asked}</span>} />
            <div className="min-w-0 flex-1">
              <Badge variant="secondary" className="mb-2 gap-1.5"><Sparkles className="size-3" /> Placement complete</Badge>
              <h1 className="text-3xl font-semibold tracking-tight">Your plan is ready</h1>
              <p className="mt-2 text-muted-foreground">
                {summary.starting_concept ? <>You&apos;ll start with <strong className="text-foreground">{summary.starting_concept}</strong> — right at the edge of what you know.</> : 'Your plan starts from the beginning, at a comfortable pace.'}
              </p>
            </div>
          </div>
          {summary.known_concepts.length ? (
            <Card className="mb-8">
              <CardHeader>
                <CardTitle>Skipping what you already know</CardTitle>
                <CardDescription>These get short spaced reviews instead of full lessons, so they stay fresh.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-wrap gap-2">
                  {summary.known_concepts.map(c => (
                    <li key={c}><Badge variant="outline" className="gap-1 border-success/30 bg-success/10"><CheckCircle2 className="size-3 text-success" /> {c}</Badge></li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          <Button asChild size="lg" className="h-11 px-6 shadow-lg shadow-primary/20">
            <Link href="/today">Go to today&apos;s plan <ArrowRight data-icon="inline-end" /></Link>
          </Button>
        </div>
      </div>
    );
  }

  const q = state?.question;
  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-8 pb-24 sm:px-6 md:pt-12">
      <div className="mb-3 flex items-center justify-between gap-4">
        <p className="flex items-center gap-2 text-sm font-medium"><Compass className="size-4 text-primary" /> Quick placement check</p>
        {state?.max_questions ? <p className="text-sm text-muted-foreground tabular-nums">Question {state.asked + 1} of at most {state.max_questions}</p> : null}
      </div>
      {state?.max_questions ? <Progress value={(100 * state.asked) / state.max_questions} className="mb-10 h-1.5" aria-label="Placement progress" /> : null}
      {q ? (
        <div key={q.id} className="grid gap-5 animate-in fade-in slide-in-from-right-4 duration-300">
          <Badge variant="outline" className="w-fit">{q.topic}</Badge>
          <h1 className="text-xl font-semibold leading-snug tracking-tight md:text-2xl">{q.prompt}</h1>
          {q.code ? <pre className="code-block">{q.code}</pre> : null}
          <div className="grid gap-2.5" role="radiogroup" aria-label="Answer choices">
            {q.options.map((option, index) => (
              <Choice key={option} role="radio" aria-checked={choice === index} selected={choice === index} marker={String.fromCharCode(65 + index)} onClick={() => setChoice(index)}>
                <span className="whitespace-pre-wrap">{option}</span>
              </Choice>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button size="lg" className="h-10 px-5" disabled={busy || choice === null} onClick={() => submit(choice)}>Submit answer</Button>
            <Button size="lg" variant="ghost" className="h-10" disabled={busy} onClick={() => submit(null)}>I don&apos;t know yet</Button>
          </div>
          <p className="text-xs text-muted-foreground">No penalty for guessing wrong or saying you don&apos;t know — this only decides where you start.</p>
        </div>
      ) : null}
      {error ? <ErrorNote message={error} /> : null}
    </div>
  );
}
