'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, Flame } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { KIND_LABEL, NAME, PACE_LABEL, activityHref, conceptHref, formatDate } from '@/lib/routes';
import type { Activity, AssessmentStatus, PlanView, Recommendations, Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, Reveal, Ring } from '@/components/common';
import { Level, PlatformTag, ProblemName } from '@/components/practice';
import Assistant from '@/components/assistant';
import { Illustration, Soc } from '@/components/socrat/illustration';
import { StatusIcon, statusFromBand } from '@/components/socrat/status';
import { WeekStrip } from '@/components/socrat/week-strip';
import { ArrowCircle, Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const VERB: Record<string, string> = { lesson: 'Start lesson', problem: 'Open problem', quiz: 'Take concept check', checkpoint: 'Start checkpoint', review: 'Start review', remedial: 'Start refresher' };
const CHIP: Record<string, string> = { lesson: 'lesson', problem: 'practice', quiz: 'check', checkpoint: 'check', review: 'review', remedial: 'review' };

function greeting(name: string) {
  const hour = new Date().getHours();
  return `${hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening'}, ${name}`;
}

/** The current module from the plan: the next milestone, with real counts only. */
function milestone(plan: PlanView | null) {
  if (!plan) return null;
  const module = plan.modules.find(m => m.concepts.some(c => c.concept === plan.current_concept)) ?? plan.modules.find(m => !m.locked_by);
  if (!module) return null;
  const finished = module.concepts.filter(c => ['mastered', 'assumed', 'practiced'].includes(c.status)).length;
  return { title: module.title, finished, total: module.concepts.length };
}

function SessionRow({ activity, done }: { activity: Activity; done: boolean }) {
  return (
    <li>
      <Link href={activityHref(activity.id)} className="group flex min-h-14 items-center gap-3 rounded-[16px] px-3 py-2 transition-colors hover:bg-raised">
        <StatusIcon status={done ? 'practised' : 'not_seen'} size={22} />
        <span className="min-w-0 flex-1">
          <span className={cn('block font-semibold', done && 'text-muted-foreground')}>{activity.title}</span>
          <span className="text-[13px] text-muted-foreground">{KIND_LABEL[activity.kind]}{activity.minutes ? `, ${activity.minutes} min` : ''}{done ? ', done' : ''}</span>
        </span>
        {!done ? <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" /> : null}
      </Link>
    </li>
  );
}

export default function TodayPage() {
  const allowed = useGuard('active');
  const { profile } = useSession();
  const [today, setToday] = useState<Today | null>(null);
  const [error, setError] = useState('');
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [plan, setPlan] = useState<PlanView | null>(null);
  const [assessment, setAssessment] = useState<AssessmentStatus | null>(null);
  const [askSoc, setAskSoc] = useState(0);

  const load = useCallback(() => {
    setError('');
    api.get<Today>('/today').then(setToday).catch(e => setError(explain(e)));
    api.get<Recommendations>('/library/recommendations?limit=4').then(setRecs).catch(() => undefined);
    api.get<PlanView>('/plan').then(setPlan).catch(() => undefined);
    api.get<{ current: AssessmentStatus }>('/assessments').then(r => setAssessment(r.current)).catch(() => undefined);
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!today && !error)) return <Loading label="Loading today" />;
  if (!today) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const name = profile?.display_name || today.greeting.split(', ').slice(1).join(', ') || 'there';
  const minutePercent = today.minutes.goal ? (100 * today.minutes.done) / today.minutes.goal : 0;
  const next = today.next;
  const review = today.queue.find(a => a.kind === 'review');
  const weak = recs?.topics.find(t => t.band === 'needs_practice');
  const goal = milestone(plan);
  const assessmentOpen = assessment && (assessment.state === 'available' || assessment.state === 'in_progress');
  const session = [...today.done.map(a => ({ a, done: true })), ...today.queue.map(a => ({ a, done: false }))];

  return (
    <Page wide>
      {/* 1. Header: phone shows "Hi, name" and today's minutes; desktop shows the greeting. */}
      <Reveal>
        <header className="mb-6 flex items-center justify-between gap-4 lg:mb-8">
          <div className="flex min-w-0 items-center gap-3">
            <span className="grid size-11 flex-none place-items-center rounded-full bg-secondary text-[15px] font-bold text-secondary-foreground lg:hidden" aria-hidden="true">{name.slice(0, 2).toUpperCase()}</span>
            <div className="min-w-0">
              <h1 className="truncate font-display text-2xl font-bold tracking-[-0.03em] lg:type-display-l lg:whitespace-normal">
                <span className="lg:hidden">Hi, {name}</span>
                <span className="hidden lg:inline">{greeting(name)}</span>
              </h1>
              <p className="text-sm text-muted-foreground lg:mt-2 lg:text-base" data-visual-mask="">
                {formatDate(today.date, { weekday: 'long', month: 'long', day: 'numeric' })}. {today.course.title}
              </p>
            </div>
          </div>
          <p className="flex-none text-right lg:hidden">
            <span className="sr-only">Today: </span>
            <span className="type-display-m tabular-nums">{today.minutes.goal}</span>
            <span className="ml-1 text-sm font-semibold text-muted-foreground">min today</span>
          </p>
        </header>
      </Reveal>

      {/* 2. Return after absence. */}
      {today.days_away >= 3 ? (
        <Reveal>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-card border px-5 py-4" role="status">
            <p className="font-semibold">Welcome back. Your plan moved forward while you were away.</p>
            <Link href="/plan#why-heading" className="text-[15px] font-semibold underline underline-offset-4">See what changed</Link>
          </div>
        </Reveal>
      ) : null}

      <div className="grid grid-cols-[minmax(0,1fr)] gap-3 sm:gap-4 lg:grid-cols-12 lg:gap-6">
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-3 sm:gap-4 lg:col-span-8 lg:gap-6">
          {/* 3. Week strip (phone and tablet). */}
          <Card className="lg:hidden" size="sm" aria-label="This week">
            <div className="px-(--card-spacing)"><WeekStrip studiedToday={today.streak.studied_today} /></div>
          </Card>

          {/* 4. Hero: the next recommended activity. */}
          <Reveal index={1}>
            {next ? (
              <Card tone="hero" className="relative min-h-72 lg:min-h-80" aria-labelledby="next-heading">
                <Illustration name="orbit" className="pointer-events-none absolute -top-4 -right-8 size-28 opacity-95 sm:-top-6 sm:-right-10 sm:size-52 lg:top-1/2 lg:right-4 lg:size-72 lg:-translate-y-1/2" />
                <div className="relative flex h-full flex-col gap-5 px-(--card-spacing) lg:max-w-[60%]">
                  <p className="type-label text-(--card-muted)">Next for you</p>
                  <div>
                    <h2 id="next-heading" className="type-display-l max-w-[14ch] pr-8 [overflow-wrap:anywhere] sm:pr-0">{next.title}</h2>
                    <p className="mt-3 max-w-md text-base text-(--card-muted)">{next.reason || 'Next in your plan.'}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Badge>{CHIP[next.kind] ?? KIND_LABEL[next.kind]}</Badge>
                    {next.minutes ? <Badge>{next.minutes} min</Badge> : null}
                  </div>
                  <div className="mt-auto">
                    <Button asChild variant="ink" size="lg">
                      <Link href={activityHref(next.id)} transitionTypes={['nav-forward']}>
                        {VERB[next.kind] ?? 'Continue'}
                        <ArrowCircle />
                      </Link>
                    </Button>
                  </div>
                </div>
              </Card>
            ) : (
              <Card tone="hero" aria-labelledby="next-heading">
                <div className="flex flex-col gap-4 px-(--card-spacing)">
                  <h2 id="next-heading" className="type-display-m">{today.study_day ? 'Done for today' : 'Rest day'}</h2>
                  <p className="max-w-md text-(--card-muted)">
                    {today.study_day
                      ? 'Everything planned for today is complete. You can keep going from your plan.'
                      : 'Today is not one of your study days. You can work ahead from your plan.'}
                  </p>
                  <div><Button asChild variant="ink" size="lg"><Link href="/plan">Open {NAME.skills}<ArrowCircle /></Link></Button></div>
                </div>
              </Card>
            )}
          </Reveal>

          {/* 5. Review due and Playground. */}
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:gap-6">
            {review || today.reviews_due ? (
              <Link href={review ? activityHref(review.id) : '/plan'} className="group flex min-h-40 flex-col justify-between gap-4 rounded-card bg-raised p-5 transition-colors hover:bg-[color-mix(in_srgb,var(--raised),var(--foreground)_5%)] lg:p-6">
                <StatusIcon status="review" size={32} />
                <span>
                  <span className="block font-display text-lg leading-tight font-bold tracking-[-0.02em]">
                    Review due{review ? `: ${review.title.replace(/^Review:?\s*/i, '')}` : ''}
                  </span>
                  {today.reviews_due > 1 ? <span className="mt-1 block text-sm text-muted-foreground">{today.reviews_due} reviews due</span> : null}
                </span>
              </Link>
            ) : null}
            <Link href="/playground" className={cn('group flex min-h-40 flex-col justify-between gap-4 rounded-card bg-secondary p-5 text-secondary-foreground transition-colors hover:bg-[color-mix(in_srgb,var(--secondary),white_8%)] lg:p-6', !(review || today.reviews_due) && 'col-span-2')}>
              <span className="type-label">{NAME.playground}</span>
              <span className="flex items-end justify-between gap-3">
                <span className="font-display text-lg leading-tight font-bold tracking-[-0.02em]">{weak ? `Explore ${weak.title} visually` : 'Ask about any concept'}</span>
                <ArrowRight className="size-5 flex-none transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
              </span>
            </Link>
          </div>

          {/* 6. Next milestone with the real module progress. */}
          {goal ? (
            <Card aria-labelledby="milestone-heading">
              <div className="grid gap-3 px-(--card-spacing)">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h2 id="milestone-heading" className="font-display text-lg font-bold tracking-[-0.02em]">Next milestone: {goal.title}</h2>
                  <span className="text-sm font-semibold text-muted-foreground tabular-nums">{goal.finished} of {goal.total} skills</span>
                </div>
                <Progress value={goal.total ? (100 * goal.finished) / goal.total : 0} aria-label={`${goal.title}: ${goal.finished} of ${goal.total} skills`} />
              </div>
            </Card>
          ) : null}

          {/* 7. Weekly assessment: a card when open, a quiet line when not ready. */}
          {assessmentOpen ? (
            <Card aria-labelledby="assessment-heading">
              <div className="flex flex-wrap items-center justify-between gap-4 px-(--card-spacing)">
                <div className="min-w-0">
                  <div className="mb-2"><Badge>{assessment.state === 'in_progress' ? 'In progress' : 'Available'}</Badge></div>
                  <h2 id="assessment-heading" className="font-display text-lg font-bold tracking-[-0.02em]">{NAME.assessment}</h2>
                  <p className="truncate text-sm text-muted-foreground">On what you studied: {assessment.topics.slice(0, 3).join(', ')}{assessment.topics.length > 3 ? ', and more' : ''}</p>
                </div>
                <Button asChild variant="outline"><Link href="/assessments">{assessment.state === 'in_progress' ? 'Continue assessment' : 'Open assessment'}</Link></Button>
              </div>
            </Card>
          ) : assessment ? (
            <p className="px-1 text-sm text-muted-foreground">{NAME.assessment}: unlocks as you study more topics this week.</p>
          ) : null}

          {/* Today's plan: what the session holds, in order. */}
          {session.length ? (
            <Card aria-labelledby="agenda-heading">
              <div className="flex items-baseline justify-between gap-3 px-(--card-spacing)">
                <h2 id="agenda-heading" className="font-display text-lg font-bold tracking-[-0.02em]">Today&apos;s session</h2>
                <span className="text-sm font-semibold text-muted-foreground tabular-nums">{today.done.length} of {session.length} done</span>
              </div>
              <ul className="grid px-[calc(var(--card-spacing)-12px)]">
                {session.map(({ a, done }) => <SessionRow key={a.id} activity={a} done={done} />)}
              </ul>
            </Card>
          ) : null}

          {/* 8. Practice recommendations. */}
          {recs?.problems.length ? (
            <section aria-labelledby="practice-heading" className="min-w-0">
              <div className="mb-3 flex items-baseline justify-between gap-3">
                <h2 id="practice-heading" className="font-display text-xl font-bold tracking-[-0.03em]">Practice picked for you</h2>
                <Link href="/library" className="text-[15px] font-semibold underline underline-offset-4">See all problems</Link>
              </div>
              <ul className="-mx-4 flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-2 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 sm:pb-0">
                {recs.problems.map(p => (
                  <li key={p.id} className="flex w-[78%] flex-none snap-start flex-col gap-3 rounded-card border bg-card p-5 sm:w-auto">
                    <div className="flex items-start justify-between gap-3">
                      <ProblemName problem={p} className="text-base" />
                      <StatusIcon status={p.status === 'solved' ? 'practised' : 'not_seen'} size={22} title={p.status === 'solved' ? 'Solved' : 'Not solved yet'} />
                    </div>
                    <p className="text-sm text-muted-foreground">{p.reason}</p>
                    <div className="mt-auto flex flex-wrap items-center gap-2"><PlatformTag platform={p.platform} /><Level problem={p} /></div>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        {/* Support column. */}
        <aside className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-3 sm:gap-4 lg:col-span-4 lg:gap-6" aria-label="Support">
          <button type="button" onClick={() => setAskSoc(n => n + 1)} className="hidden items-center gap-4 rounded-card border bg-card p-5 text-left transition-colors hover:bg-raised lg:flex" aria-haspopup="dialog">
            <Soc size={56} />
            <span className="min-w-0">
              <span className="block font-display text-lg font-bold tracking-[-0.02em]">Ask Soc</span>
              <span className="block text-sm text-muted-foreground">Your tutor asks before it tells.</span>
            </span>
          </button>

          <Card className="hidden lg:flex" aria-labelledby="week-heading">
            <div className="grid gap-4 px-(--card-spacing)">
              <div className="flex items-center justify-between gap-3">
                <h2 id="week-heading" className="flex items-center gap-2 font-display text-lg font-bold tracking-[-0.02em]">
                  <Flame className="size-5" strokeWidth={1.5} aria-hidden="true" /> {today.streak.current}-day streak
                </h2>
                <Ring value={minutePercent} size={56} ariaLabel={`${today.minutes.done} of ${today.minutes.goal} minutes today`} label={<span className="text-[13px]">{today.minutes.done}</span>} />
              </div>
              <WeekStrip studiedToday={today.streak.studied_today} />
              <p className="text-sm text-muted-foreground">
                {today.minutes.done} of {today.minutes.goal} min today. {today.streak.week_minutes} of {today.streak.week_goal} min this week.
              </p>
            </div>
          </Card>

          {recs?.topics.length ? (
            <Card aria-labelledby="learn-next-heading">
              <div className="px-(--card-spacing)">
                <h2 id="learn-next-heading" className="mb-3 font-display text-lg font-bold tracking-[-0.02em]">Skills to learn next</h2>
                <ul className="grid gap-1">
                  {recs.topics.map(t => (
                    <li key={t.id}>
                      <Link href={conceptHref(t.id)} className="-mx-2 flex min-h-12 items-start gap-3 rounded-[14px] px-2 py-2 transition-colors hover:bg-raised">
                        <StatusIcon status={statusFromBand(t.band)} size={22} className="mt-0.5" />
                        <span className="min-w-0">
                          <span className="block font-semibold">{t.title}</span>
                          <span className="block text-[13px] text-muted-foreground">{t.reason}</span>
                        </span>
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            </Card>
          ) : null}

          {/* 9. Course progress: ring with the real percent. */}
          <Card aria-labelledby="course-heading">
            <div className="flex items-center gap-5 px-(--card-spacing)">
              <Ring value={today.progress.percent} size={80} label={<span className="text-base">{today.progress.percent}%</span>} ariaLabel={`Course ${today.progress.percent} percent complete`} />
              <div className="min-w-0">
                <h2 id="course-heading" className="font-display text-lg font-bold tracking-[-0.02em]">Course progress</h2>
                <p className="text-sm text-muted-foreground">{today.progress.finished} of {today.progress.total} skills. {PACE_LABEL[today.pace]} pace.</p>
                <p className="mt-1 text-sm text-muted-foreground" data-visual-mask="">Projected finish {formatDate(today.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })}</p>
              </div>
            </div>
          </Card>
          <Link href="/progress" className="flex min-h-12 items-center justify-between gap-3 rounded-card border px-5 py-3 text-[15px] font-semibold transition-colors hover:bg-raised">
            Check your progress in {NAME.evidence}
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </aside>
      </div>
      <Assistant scope="general" title="Ask Soc" openSignal={askSoc} launcher="phone" />
    </Page>
  );
}
