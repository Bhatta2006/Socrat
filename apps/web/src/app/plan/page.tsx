'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Check, CircleDot, Gauge, History, Hourglass, Target } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { KIND_LABEL, PACE_LABEL, activityHref, conceptHref, formatDate, formatStamp, hours } from '@/lib/routes';
import type { PlanView, RoadmapItem } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, PageHeader, Reveal, StatCard } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const STATUS: Record<RoadmapItem['status'], { label: string; tone: string }> = {
  mastered: { label: 'Mastered', tone: 'border-primary bg-primary text-primary-foreground' },
  assumed: { label: 'Already known', tone: 'border-success bg-success/80 text-success-foreground' },
  practiced: { label: 'Practiced', tone: 'border-primary/50 bg-primary/15 text-primary' },
  in_progress: { label: 'In progress', tone: 'border-primary text-primary ring-4 ring-primary/15' },
  upcoming: { label: 'Upcoming', tone: 'border-border text-muted-foreground' },
};

export default function PlanPage() {
  const allowed = useGuard('active');
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<PlanView>('/plan').then(setPlan).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!plan && !error)) return <Loading />;
  if (!plan) return <Page><ErrorNote message={error} retry={load} /></Page>;

  return (
    <Page>
      <Reveal>
        <PageHeader
          eyebrow="Your plan"
          title={<>Finish by {formatDate(plan.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}</>}
          description={plan.pace_reason}
          actions={plan.target_date ? (
            <Badge variant="outline" className={cn('h-7 px-3', plan.on_track ? 'border-success/30 bg-success/10 text-success' : 'border-warning/40 bg-warning/10')}>
              {plan.on_track ? 'On track for' : 'Behind target of'} {formatDate(plan.target_date)}
            </Badge>
          ) : null}
        />
      </Reveal>
      {plan.target_date && plan.on_track === false ? (
        <p className="-mt-4 mb-6 text-sm">To hit your target, add a study day or more minutes per day in <Link href="/settings" className="font-medium text-primary underline underline-offset-2">settings</Link>.</p>
      ) : null}

      <Reveal index={1} className="mb-8 grid gap-4 sm:grid-cols-3">
        <StatCard icon={<Gauge />} label="Pace" value={PACE_LABEL[plan.pace]} hint="Adapts to your results" />
        <StatCard icon={<Hourglass />} label="Study left" value={hours(plan.remaining_minutes)} hint="At your current pace" />
        <StatCard icon={<Target />} label="Concepts done" value={`${plan.progress.finished}/${plan.progress.total}`} hint={<Progress value={plan.progress.percent} className="mt-2 h-1.5" />} />
      </Reveal>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px]">
        <section aria-labelledby="roadmap-heading" className="min-w-0">
          <h2 id="roadmap-heading" className="mb-4 text-lg font-semibold">Roadmap</h2>
          <ol className="grid gap-4">
            {plan.modules.map((module, mi) => {
              const done = module.concepts.filter(c => ['mastered', 'assumed', 'practiced'].includes(c.status)).length;
              return (
                <Reveal key={module.id} index={mi + 2}>
                  <Card size="sm">
                    <CardHeader>
                      <CardTitle className="text-base font-semibold">{module.title}</CardTitle>
                      <CardDescription>
                        {module.bridge ? <span className="mr-1 font-medium text-primary">Bridge from {module.course} ·</span> : null}
                        {module.summary}
                      </CardDescription>
                      <CardAction><span className="text-xs font-medium text-muted-foreground tabular-nums">{done}/{module.concepts.length}</span></CardAction>
                    </CardHeader>
                    <CardContent>
                      <Progress value={module.concepts.length ? (100 * done) / module.concepts.length : 0} className="mb-3 h-1" aria-label={`${module.title} progress`} />
                      <ul className="-mx-2 grid">
                        {module.concepts.map(c => {
                          const s = STATUS[c.status];
                          const current = c.concept === plan.current_concept;
                          return (
                            <li key={c.concept}>
                              <Link href={conceptHref(c.concept)} className={cn('flex items-center gap-3 rounded-lg px-2 py-2 transition-colors hover:bg-muted', current && 'bg-primary/5')}>
                                <span className={cn('grid size-6 flex-none place-items-center rounded-full border text-xs', s.tone)} aria-hidden="true">
                                  {['mastered', 'assumed'].includes(c.status) ? <Check className="size-3.5" /> : c.status === 'in_progress' ? <CircleDot className="size-3.5" /> : null}
                                </span>
                                <span className="min-w-0 flex-1 text-sm">
                                  {c.title}
                                  {current ? <Badge className="ml-2 h-5">current</Badge> : null}
                                </span>
                                <span className="text-xs text-muted-foreground">{s.label}</span>
                              </Link>
                            </li>
                          );
                        })}
                      </ul>
                    </CardContent>
                  </Card>
                </Reveal>
              );
            })}
          </ol>
        </section>

        <aside className="grid content-start gap-6 lg:sticky lg:top-20 lg:self-start">
          <Card aria-labelledby="schedule-heading">
            <CardHeader>
              <CardTitle id="schedule-heading" className="flex items-center gap-2"><CalendarClock className="size-4 text-primary" /> Next two weeks</CardTitle>
            </CardHeader>
            <CardContent>
              <ol className="relative grid gap-4 border-l pl-4">
                {plan.days.map((day, index) => (
                  <li key={day.date} className="relative">
                    <span className={cn('absolute top-1.5 -left-[21px] size-2.5 rounded-full border-2 border-background', index === 0 ? 'bg-primary' : 'bg-muted-foreground/40')} />
                    <div className="mb-1 flex items-baseline justify-between">
                      <span className={cn('text-sm font-semibold', index === 0 && 'text-primary')}>{index === 0 ? 'Today' : formatDate(day.date, { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                      <span className="text-xs text-muted-foreground tabular-nums">{day.minutes} min</span>
                    </div>
                    <ul className="grid gap-0.5">
                      {day.items.map(item => (
                        <li key={item.id} className="text-sm">
                          <Link href={activityHref(item.id)} className="hover:text-primary hover:underline">{item.title}</Link>
                          <span className="text-xs text-muted-foreground"> · {KIND_LABEL[item.kind]}</span>
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ol>
            </CardContent>
          </Card>
          {plan.reasons.length || plan.revisions.length ? (
            <Card aria-labelledby="why-heading">
              <CardHeader>
                <CardTitle id="why-heading" className="flex items-center gap-2"><History className="size-4 text-primary" /> Why the plan looks like this</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="grid gap-2 text-sm">
                  {plan.reasons.map(r => <li key={r} className="flex gap-2"><span className="mt-2 size-1.5 flex-none rounded-full bg-primary" />{r}</li>)}
                </ul>
                {plan.revisions.length ? (
                  <>
                    <h3 className="mt-5 mb-2 text-xs font-medium text-muted-foreground">Recent changes</h3>
                    <ol className="grid gap-3 text-sm">
                      {plan.revisions.map(rev => (
                        <li key={rev.at} className="rounded-lg border bg-muted/30 p-3">
                          <p className="text-xs text-muted-foreground">{formatStamp(rev.at)} · {PACE_LABEL[rev.pace]} · finish {formatDate(rev.projected_finish)}</p>
                          {rev.reasons.map(r => <p key={r} className="mt-1">{r}</p>)}
                        </li>
                      ))}
                    </ol>
                  </>
                ) : null}
              </CardContent>
            </Card>
          ) : null}
        </aside>
      </div>
    </Page>
  );
}
