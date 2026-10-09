'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Clock, Flame, GraduationCap, Trophy } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { BAND_LABEL, PACE_LABEL, conceptHref, formatDate, formatStamp, hours } from '@/lib/routes';
import type { Band, ProgressView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BandBadge, ErrorNote, Loading, NumberTicker, Page, PageHeader, Reveal, Ring, StatCard } from '@/components/common';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const KIND: Record<string, string> = { quiz: 'Concept check', code: 'Problem', checkpoint: 'Checkpoint', review: 'Review', placement: 'Placement', external: 'Practice', verified: 'Codeforces' };
const BANDS: Band[] = ['strong', 'likely_known', 'developing', 'needs_practice', 'not_started'];

function level(minutes: number) {
  if (!minutes) return 0;
  if (minutes < 15) return 1;
  if (minutes < 30) return 2;
  if (minutes < 60) return 3;
  return 4;
}

export default function ProgressPage() {
  const allowed = useGuard('active');
  const [data, setData] = useState<ProgressView | null>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    api.get<ProgressView>('/progress').then(setData).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);

  if (!allowed || (!data && !error)) return <Loading />;
  if (!data) return <Page><ErrorNote message={error} retry={load} /></Page>;

  const weekPercent = data.week.goal ? (100 * data.week.minutes) / data.week.goal : 0;
  const counts = Object.fromEntries(BANDS.map(b => [b, 0])) as Record<Band, number>;
  data.modules.forEach(m => m.concepts.forEach(c => { counts[c.band] += 1; }));
  const totalConcepts = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const leading = (7 + new Date(`${data.heatmap[0]?.day}T00:00:00`).getDay() - 1) % 7;

  return (
    <Page>
      <Reveal>
        <PageHeader eyebrow="Progress" title={<>{data.progress.percent}% of the way there</>} description={`Projected finish ${formatDate(data.projected_finish, { month: 'long', day: 'numeric', year: 'numeric' })} · ${PACE_LABEL[data.pace]} pace`} />
      </Reveal>

      <Reveal index={1} className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="gap-0">
          <CardContent className="flex items-center gap-4">
            <Ring value={data.progress.percent} size={60} label={`${data.progress.percent}%`} />
            <div>
              <p className="text-xs font-medium text-muted-foreground">Course</p>
              <p className="text-lg font-semibold">{data.progress.finished}/{data.progress.total} concepts</p>
            </div>
          </CardContent>
        </Card>
        <Card className="gap-0">
          <CardContent className="flex items-center gap-4">
            <Ring value={weekPercent} size={60} tone="streak" label={<Clock className="size-4 text-streak" />} />
            <div>
              <p className="text-xs font-medium text-muted-foreground">This week</p>
              <p className="text-lg font-semibold tabular-nums">{data.week.minutes}<span className="text-sm font-normal text-muted-foreground"> / {data.week.goal} min</span></p>
            </div>
          </CardContent>
        </Card>
        <StatCard icon={<Flame className="text-streak" />} label="Day streak" value={<NumberTicker value={data.streak.current} />} hint={`Best: ${data.streak.longest} days`} />
        <StatCard icon={<Trophy />} label="Problems solved" value={<><NumberTicker value={data.solves.independent_solves} /><span className="text-base font-normal text-muted-foreground"> + {data.solves.assisted_solves}</span></>} hint="Alone + with hints" />
      </Reveal>

      <Reveal index={2}>
        <Card className="mb-8" aria-labelledby="activity-heading">
          <CardHeader>
            <CardTitle id="activity-heading">Study activity</CardTitle>
            <CardDescription>{hours(data.total_minutes)} in the last 6 months</CardDescription>
            <CardAction>
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                Less <span className="heatmap !grid-rows-[12px] !overflow-visible !p-0" aria-hidden="true">{[0, 1, 2, 3, 4].map(l => <span key={l} data-level={l} />)}</span> More
              </span>
            </CardAction>
          </CardHeader>
          <CardContent>
            <div className="heatmap" role="img" aria-label={`Daily study minutes for the last ${data.heatmap.length} days`}>
              {Array.from({ length: leading }, (_, i) => <span key={`pad-${i}`} style={{ visibility: 'hidden' }} />)}
              {data.heatmap.map(d => (
                <span key={d.day} data-level={level(d.minutes)} title={`${formatDate(d.day)}: ${d.minutes} min, ${d.activities} activities`} />
              ))}
            </div>
          </CardContent>
        </Card>
      </Reveal>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <section aria-labelledby="mastery-heading" className="min-w-0">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <h2 id="mastery-heading" className="text-lg font-semibold">Mastery by concept</h2>
          </div>
          <div className="mb-5 flex h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
            {BANDS.map(b => <span key={b} className={cn('h-full', `band-${b}`)} style={{ width: `${(100 * counts[b]) / totalConcepts}%`, borderRadius: 0, opacity: 1 }} />)}
          </div>
          <ul className="mb-5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {BANDS.map(b => <li key={b} className="flex items-center gap-1.5"><span className={`band-dot band-${b}`} aria-hidden="true" />{BAND_LABEL[b]} <span className="tabular-nums">({counts[b]})</span></li>)}
          </ul>
          <div className="grid gap-4">
            {data.modules.map(m => (
              <Card key={m.id} size="sm">
                <CardHeader><CardTitle className="font-semibold">{m.title}</CardTitle></CardHeader>
                <CardContent>
                  <ul className="-mx-2 grid">
                    {m.concepts.map(c => (
                      <li key={c.id}>
                        <Link href={conceptHref(c.id)} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-1 rounded-lg px-2 py-2 transition-colors hover:bg-muted sm:grid-cols-[minmax(0,1fr)_160px_130px]">
                          <span className="text-sm">{c.title}</span>
                          <span className="hidden sm:block">
                            <Progress value={c.evidence ? Math.round(c.mastery * 100) : 0} className="h-1.5" aria-label={`${c.title} mastery`} />
                          </span>
                          <BandBadge band={c.band} />
                        </Link>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <aside className="grid content-start gap-6 lg:sticky lg:top-20 lg:self-start">
          <Card aria-labelledby="recent-heading">
            <CardHeader><CardTitle id="recent-heading">Recent results</CardTitle></CardHeader>
            <CardContent>
              {data.recent.length ? (
                <ul className="grid divide-y text-sm">
                  {data.recent.map((r, i) => {
                    const pct = Math.round(r.score * 100);
                    return (
                      <li key={i} className="flex items-center justify-between gap-3 py-2.5">
                        <span className="min-w-0">
                          <span className="block truncate font-medium">{r.concept}</span>
                          <span className="text-xs text-muted-foreground">{KIND[r.kind] ?? r.kind}{r.assisted ? ' · with hints' : ''} · {formatStamp(r.at)}</span>
                        </span>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className={cn('rounded-md px-2 py-0.5 text-xs font-semibold tabular-nums', pct >= 80 ? 'bg-success/15 text-success' : pct < 50 ? 'bg-destructive/10 text-destructive' : 'bg-warning/15 text-warning-foreground dark:text-warning')}>{pct}%</span>
                          </TooltipTrigger>
                          <TooltipContent>Score</TooltipContent>
                        </Tooltip>
                      </li>
                    );
                  })}
                </ul>
              ) : (
                <Empty className="border-0 p-4">
                  <EmptyHeader>
                    <EmptyMedia variant="icon"><GraduationCap /></EmptyMedia>
                    <EmptyTitle>No results yet</EmptyTitle>
                    <EmptyDescription>Finish a concept check or problem to see results here.</EmptyDescription>
                  </EmptyHeader>
                </Empty>
              )}
            </CardContent>
          </Card>
        </aside>
      </div>
    </Page>
  );
}
