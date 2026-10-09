'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, BookOpen, CheckCircle2, Circle, Code2, Flame, ListChecks, RotateCcw, Sparkles, Target, Trophy } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { KIND_LABEL, PACE_LABEL, activityHref, conceptHref, formatDate, hours } from '@/lib/routes';
import type { Activity, ActivityKind, Recommendations, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BandBadge, ErrorNote, Loading, Page, Reveal, Ring } from '@/components/common';
import { Level, LevelCard, PlatformTag, ProblemName } from '@/components/practice';
import { celebrateOnce } from '@/components/celebrate';
import Assistant from '@/components/assistant';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const KIND_ICON: Record<ActivityKind, typeof BookOpen> = {
  lesson: BookOpen,
  quiz: ListChecks,
  problem: Code2,
  checkpoint: Trophy,
  review: RotateCcw,
  remedial: RotateCcw,
};

function ActivityRow({ activity, done = false }: { activity: Activity; done?: boolean }) {
  const Icon = KIND_ICON[activity.kind] ?? BookOpen;
  return (
    <li>
      <Link
        href={activityHref(activity.id)}
        className="group flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors hover:bg-muted/60"
      >
        {done ? (
          <CheckCircle2 className="size-5 flex-none text-success" aria-hidden="true" />
        ) : (
          <Circle className="size-5 flex-none text-muted-foreground/50" aria-hidden="true" />
        )}
        <span className="min-w-0 flex-1">
          <span className={cn('block text-sm font-medium', done && 'text-muted-foreground line-through decoration-1')}>{activity.title}</span>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Icon className="size-3" aria-hidden="true" />
            {KIND_LABEL[activity.kind]}{activity.minutes ? ` · ${activity.minutes} min` : ''}
          </span>
        </span>
        <span className="sr-only">{done ? 'completed' : 'not started'}</span>
        {!done ? <ArrowRight className="size-4 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" aria-hidden="true" /> : null}
      </Link>
    </li>
  );
}

/** Seven dots ending today: what's at stake if the learner skips. */
function WeekStrip({ current, studiedToday }: { current: number; studiedToday: boolean }) {
  const days = Array.from({ length: 7 }, (_, i) => 6 - i);
  return (
    <div className="flex items-end gap-1.5" aria-hidden="true">
      {days.map(offset => {
        const isToday = offset === 0;
        const lit = isToday ? studiedToday : offset <= current - (studiedToday ? 1 : 0);
        const date = new Date(Date.now() - offset * 86400000);
        return (
          <div key={offset} className="grid justify-items-center gap-1">
            <span
              className={cn(
                'grid size-7 place-items-center rounded-full border text-[10px] font-semibold',
                lit ? 'border-streak/40 bg-streak text-white' : 'bg-muted/50 text-muted-foreground',
                isToday && !lit && 'border-dashed border-streak/60',
              )}
            >
              {lit ? <Flame className="size-3.5 fill-current" /> : null}
            </span>
            <span className={cn('text-[10px] text-muted-foreground', isToday && 'font-semibold text-foreground')}>
              {date.toLocaleDateString(undefined, { weekday: 'narrow' })}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function motivation(today: Today): string {
  const left = Math.max(0, today.minutes.goal - today.minutes.done);
  if (!today.study_day) return 'A rest day on your schedule — a short review still counts toward your streak.';
  if (left === 0) return 'Daily goal reached. Anything more is a bonus.';
  if (!today.streak.studied_today && today.streak.current > 0)
    return `About ${left} minutes to keep your ${today.streak.current}-day streak going.`;
  if (today.minutes.done > 0) return `${left} minutes to go — you're ${Math.round((100 * today.minutes.done) / today.minutes.goal)}% of the way.`;
  return `Your ${today.minutes.goal}-minute session is ready. Start with one step.`;
}

export default function TodayPage() {
  const allowed = useGuard('active');
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState('');
  const [recs, setRecs] = useState<Recommendations | null>(null);

  const load = useCallback(() => {
    setError('');
    api.get<Today>('/today').then(setToday).catch(e => setError(explain(e)));
    api.get<Recommendations>('/library/recommendations?limit=4').then(setRecs).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  useEffect(() => {
    if (today && today.minutes.goal && today.minutes.done >= today.minutes.goal) celebrateOnce(`socrat-goal-${today.date}`, 'big');
  }, [today]);

  if (!allowed || (!today && !error)) return <Loading />;
  if (!today) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const minutePercent = today.minutes.goal ? (100 * today.minutes.done) / today.minutes.goal : 0;
  const next = today.next;
  const total = today.done.length + today.queue.length;
  const NextIcon = next ? KIND_ICON[next.kind] ?? BookOpen : Sparkles;

  return (
    <Page>
      <Reveal>
        <header className="mb-8 flex flex-wrap items-end justify-between gap-6">
          <div className="min-w-0">
            <p className="mb-1.5 text-sm text-muted-foreground">
              {formatDate(today.date, { weekday: 'long', month: 'long', day: 'numeric' })} · {today.course.title}
            </p>
            <h1 className="text-3xl font-semibold tracking-tight md:text-4xl">{today.greeting}</h1>
            <p className="mt-1.5 text-muted-foreground">{motivation(today)}</p>
          </div>
        </header>
      </Reveal>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="grid min-w-0 content-start gap-6">
          <Reveal index={1}>
            {next ? (
              <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-primary/12 via-card to-card ring-primary/20">
                <div className="bg-grid pointer-events-none absolute inset-0 opacity-40 [mask-image:linear-gradient(to_left,black,transparent_60%)]" aria-hidden="true" />
                <CardContent className="relative flex flex-wrap items-center justify-between gap-6 py-2">
                  <div className="min-w-0 max-w-xl">
                    <Badge variant="secondary" className="mb-3 gap-1.5 bg-background/70">
                      <NextIcon className="size-3" /> Up next · {KIND_LABEL[next.kind]}{next.minutes ? ` · ${next.minutes} min` : ''}
                    </Badge>
                    <h2 id="next-heading" className="text-2xl font-semibold tracking-tight md:text-3xl">{next.title}</h2>
                    {next.reason ? <p className="mt-2 text-sm text-muted-foreground">{next.reason}</p> : null}
                    <Button asChild size="lg" className="mt-5 h-10 px-5 text-sm shadow-sm shadow-primary/20">
                      <Link href={activityHref(next.id)}>
                        {next.kind === 'lesson' ? 'Start lesson' : next.kind === 'problem' ? 'Open problem' : 'Begin'}
                        <ArrowRight data-icon="inline-end" />
                      </Link>
                    </Button>
                  </div>
                  <Ring value={minutePercent} size={112} stroke={9} label={
                    <span className="grid justify-items-center leading-tight">
                      <span className="text-xl font-semibold">{today.minutes.done}</span>
                      <span className="text-[11px] font-normal text-muted-foreground">of {today.minutes.goal} min</span>
                    </span>
                  } />
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="flex flex-wrap items-center gap-5 py-2">
                  <span className="grid size-12 place-items-center rounded-full bg-success/15 text-success"><Trophy className="size-6" /></span>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-xl font-semibold">{today.study_day ? "You're done for today" : 'Rest day'}</h2>
                    <p className="text-sm text-muted-foreground">
                      {today.study_day
                        ? 'Everything planned for today is complete. Rest helps it stick — or keep going from your plan.'
                        : "Today isn't one of your study days. Come back tomorrow, or work ahead from your plan."}
                    </p>
                  </div>
                  <Button asChild variant="outline"><Link href="/plan">Open my plan</Link></Button>
                </CardContent>
              </Card>
            )}
          </Reveal>

          {total ? (
            <Reveal index={2}>
              <Card aria-labelledby="agenda-heading">
                <CardHeader>
                  <CardTitle id="agenda-heading">Today&apos;s session</CardTitle>
                  <CardDescription>{today.done.length} of {total} done</CardDescription>
                  <CardAction>
                    {today.reviews_due ? <Badge variant="outline" className="border-warning/40 bg-warning/10">{today.reviews_due} review{today.reviews_due > 1 ? 's' : ''} due</Badge> : null}
                  </CardAction>
                </CardHeader>
                <CardContent>
                  <Progress value={total ? (100 * today.done.length) / total : 0} className="mb-3 h-1.5" aria-label="Session progress" />
                  <ul className="-mx-3 grid">
                    {today.done.map(a => <ActivityRow key={a.id} activity={a} done />)}
                    {today.queue.map(a => <ActivityRow key={a.id} activity={a} />)}
                  </ul>
                </CardContent>
              </Card>
            </Reveal>
          ) : null}

          {recs?.problems.length ? (
            <Reveal index={3}>
              <Card aria-labelledby="practice-heading">
                <CardHeader>
                  <CardTitle id="practice-heading">Practice picked for you</CardTitle>
                  <CardDescription>Matched to your level, skipping what you&apos;ve solved</CardDescription>
                  <CardAction><Button asChild variant="ghost" size="sm"><Link href="/library">Open library <ArrowRight data-icon="inline-end" /></Link></Button></CardAction>
                </CardHeader>
                <CardContent>
                  <ul className="grid gap-1">
                    {recs.problems.map(p => (
                      <li key={p.id} className="-mx-2 flex flex-wrap items-start justify-between gap-2 rounded-lg px-2 py-2.5 transition-colors hover:bg-muted/50">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <ProblemName problem={p} />
                            <PlatformTag platform={p.platform} />
                          </div>
                          <p className="mt-0.5 text-xs text-muted-foreground">{p.reason}</p>
                        </div>
                        <Level problem={p} />
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </Reveal>
          ) : null}
        </div>

        <aside className="grid content-start gap-6">
          <Reveal index={1}>
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><Flame className="size-4 text-streak" /> {today.streak.current}-day streak</CardTitle>
                <CardDescription>{today.streak.studied_today ? 'Secured for today. See you tomorrow.' : 'Study today to keep it alive.'}</CardDescription>
              </CardHeader>
              <CardContent>
                <WeekStrip current={today.streak.current} studiedToday={today.streak.studied_today} />
                <p className="mt-3 text-xs text-muted-foreground">Longest: {today.streak.longest} days · {hours(today.minutes.goal)} per study day</p>
              </CardContent>
            </Card>
          </Reveal>
          {recs ? (
            <Reveal index={2}>
              <Card>
                <CardContent className="grid gap-5">
                  <LevelCard level={recs.level} solved={recs.solved_external} />
                  {recs.topics.length ? (
                    <div className="border-t pt-4">
                      <h2 className="mb-2 flex items-center gap-1.5 text-sm font-medium"><Target className="size-3.5 text-primary" /> Learn next</h2>
                      <ul className="grid gap-3">
                        {recs.topics.map(t => (
                          <li key={t.id}>
                            <Link href={conceptHref(t.id)} className="text-sm font-medium hover:text-primary hover:underline">{t.title}</Link>
                            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                              <BandBadge band={t.band} />
                              <span>{t.reason}</span>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </Reveal>
          ) : null}
          <Reveal index={3}>
            <Card>
              <CardHeader>
                <CardTitle>Course progress</CardTitle>
                <CardDescription>{today.progress.finished} of {today.progress.total} concepts · {PACE_LABEL[today.pace]} pace</CardDescription>
                <CardAction><span className="text-lg font-semibold tabular-nums">{today.progress.percent}%</span></CardAction>
              </CardHeader>
              <CardContent>
                <Progress value={today.progress.percent} className="h-2" aria-label="Course progress" />
                <p className="mt-3 text-xs text-muted-foreground">
                  Projected finish <span className="font-medium text-foreground">{formatDate(today.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}</span>
                </p>
                {today.latest_update?.reasons.length ? (
                  <ul className="mt-3 grid gap-1 border-t pt-3 text-xs text-muted-foreground">
                    {today.latest_update.reasons.slice(0, 2).map(r => <li key={r}>• {r}</li>)}
                  </ul>
                ) : null}
              </CardContent>
            </Card>
          </Reveal>
        </aside>
      </div>
      <Assistant scope="general" title="Ask your tutor" />
    </Page>
  );
}
