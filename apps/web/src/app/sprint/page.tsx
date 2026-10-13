'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { ArrowRight, CheckCircle2, Circle, ExternalLink, Flag, Timer, Zap } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { formatStamp } from '@/lib/routes';
import type { SprintView } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Difficulty, ErrorNote, Loading, Page, PageHeader, Ring } from '@/components/common';
import { celebrate } from '@/components/celebrate';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';

interface Overview {
  current: SprintView | null;
  history: { id: string; started_at: number; solved: number; total: number; minutes: number }[];
}

function clock(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

function useCountdown(seconds: number | null, onExpire: () => void) {
  const [left, setLeft] = useState(seconds ?? 0);
  useEffect(() => {
    if (seconds === null) return;
    setLeft(seconds);
    const started = Date.now();
    const timer = setInterval(() => {
      const next = Math.max(0, seconds - Math.floor((Date.now() - started) / 1000));
      setLeft(next);
      if (next === 0) { clearInterval(timer); onExpire(); }
    }, 1000);
    return () => clearInterval(timer);
  }, [seconds, onExpire]);
  return left;
}

function Running({ sprint, refresh, finish, busy }: { sprint: SprintView; refresh: () => void; finish: () => void; busy: boolean }) {
  const left = useCountdown(sprint.seconds_left, refresh);
  const total = sprint.deadline - sprint.started_at;
  useEffect(() => {
    const onFocus = () => refresh();
    window.addEventListener('focus', onFocus);
    return () => window.removeEventListener('focus', onFocus);
  }, [refresh]);
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_280px]">
      <div className="grid gap-3">
        {sprint.problems.map((p, i) => (
          <Card key={p.id} className={cn('transition-colors', p.solved_after !== null && 'ring-success/40 bg-success/5')}>
            <CardContent className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <span className="grid size-8 flex-none place-items-center rounded-full border text-sm font-semibold">{i + 1}</span>
                <div className="min-w-0">
                  <p className="font-medium">{p.title}</p>
                  <p className="text-xs text-muted-foreground">{p.concept}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Difficulty level={p.difficulty} />
                {p.solved_after !== null ? (
                  <Badge variant="outline" className="gap-1 border-success/30 bg-success/10 text-success"><CheckCircle2 className="size-3" /> {clock(p.solved_after)}</Badge>
                ) : (
                  <Button asChild size="sm" variant="outline">
                    <a href={`/problems/${p.id}`} target="_blank" rel="noopener noreferrer">Solve <ExternalLink data-icon="inline-end" /></a>
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        <p className="text-xs text-muted-foreground">Problems open in a new tab so the clock stays here. A solve counts when Submit is accepted.</p>
      </div>
      <Card className="h-fit lg:sticky lg:top-20">
        <CardContent className="grid justify-items-center gap-4 py-2 text-center">
          <Ring value={total ? (100 * left) / total : 0} size={120} stroke={9} tone={left < 300 ? 'streak' : 'primary'} label={<span role="timer" className="text-xl tabular-nums">{clock(left)}</span>} />
          <p className="text-sm text-muted-foreground">{sprint.solved} of {sprint.problems.length} solved</p>
          <div className="flex flex-wrap justify-center gap-2">
            <Button variant="outline" size="sm" onClick={refresh}>Refresh</Button>
            <Button size="sm" disabled={busy} onClick={finish}><Flag data-icon="inline-start" /> Finish</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function Result({ sprint }: { sprint: SprintView }) {
  useEffect(() => { if (sprint.solved === sprint.problems.length) celebrate('big'); else if (sprint.solved) celebrate('small'); }, [sprint]);
  return (
    <Card>
      <CardContent className="grid gap-5">
        <div className="flex flex-wrap items-center gap-5">
          <Ring value={(100 * sprint.solved) / sprint.problems.length} size={96} stroke={8} tone={sprint.solved ? 'success' : 'primary'} label={<span className="text-lg">{sprint.solved}/{sprint.problems.length}</span>} />
          <div>
            <h2 className="text-2xl font-semibold tracking-tight">{sprint.solved === sprint.problems.length ? 'Clean sweep' : sprint.solved ? 'Good sprint' : 'Every sprint makes the next one faster'}</h2>
            <p className="text-muted-foreground">Unsolved problems stay in your recommendations so you can finish them calmly.</p>
          </div>
        </div>
        <ul className="grid gap-2">
          {sprint.problems.map(p => (
            <li key={p.id} className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
              <span className="flex items-center gap-2">
                {p.solved_after !== null ? <CheckCircle2 className="size-4 text-success" /> : <Circle className="size-4 text-muted-foreground" />}
                <Link href={`/problems/${p.id}`} className="font-medium hover:text-primary hover:underline">{p.title}</Link>
              </span>
              <span className="tabular-nums text-muted-foreground">{p.solved_after !== null ? `solved in ${clock(p.solved_after)}` : 'not yet'}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

export default function Sprint() {
  const allowed = useGuard('active');
  const [overview, setOverview] = useState<Overview | null>(null);
  const [view, setView] = useState<SprintView | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    api.get<Overview>('/library/sprints').then(o => { setOverview(o); if (o.current) setView(o.current); }).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => { if (allowed) load(); }, [allowed, load]);
  const refresh = useCallback(() => {
    if (view) api.get<SprintView>(`/library/sprints/${view.id}`).then(setView).catch(() => undefined);
  }, [view]);

  async function start() {
    setBusy(true);
    setError('');
    try { setView(await api.post<SprintView>('/library/sprints')); } catch (e) { setError(explain(e)); } finally { setBusy(false); }
  }
  async function finish() {
    if (!view) return;
    setBusy(true);
    try { setView(await api.post<SprintView>(`/library/sprints/${view.id}/finish`)); load(); } catch (e) { setError(explain(e)); } finally { setBusy(false); }
  }

  if (!allowed || (!overview && !error)) return <Loading />;
  return (
    <Page>
      <PageHeader eyebrow="Focus sprint" title="Three problems. One clock." description="Problems picked just above where you are, from topics you've studied. Solve as many as you can before time runs out." />
      {view && !view.finished ? <Running sprint={view} refresh={refresh} finish={finish} busy={busy} /> : view?.finished ? (
        <div className="grid gap-4">
          <Result sprint={view} />
          <Button className="w-fit" onClick={() => { setView(null); start(); }} disabled={busy}><Zap data-icon="inline-start" /> Start another sprint</Button>
        </div>
      ) : (
        <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-streak/12 via-card to-card ring-streak/20">
          <CardContent className="grid gap-4 py-2">
            <span className="grid size-12 place-items-center rounded-xl bg-streak/15 text-streak"><Timer className="size-6" /></span>
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">Ready when you are</h2>
              <p className="mt-1 max-w-xl text-muted-foreground">45 minutes, three judged problems, easiest first. Your tutor stays available — but the clock keeps running.</p>
            </div>
            <Button size="lg" className="h-10 w-fit px-5" disabled={busy} onClick={start}>{busy ? <Spinner /> : <Zap data-icon="inline-start" />} Start sprint</Button>
          </CardContent>
        </Card>
      )}
      {error ? <ErrorNote message={error} /> : null}
      {overview?.history.length ? (
        <Card className="mt-8">
          <CardHeader><CardTitle>Past sprints</CardTitle><CardDescription>Solved count and time used</CardDescription></CardHeader>
          <CardContent>
            <ul className="grid divide-y text-sm">
              {overview.history.map(h => (
                <li key={h.id} className="flex items-center justify-between py-2">
                  <span>{formatStamp(h.started_at)}</span>
                  <span className="tabular-nums text-muted-foreground">{h.solved}/{h.total} solved · {h.minutes} min</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      ) : null}
      <p className="mt-6 text-sm"><Link href="/library" className="inline-flex items-center gap-1 text-primary hover:underline">Back to the library <ArrowRight className="size-3.5" /></Link></p>
    </Page>
  );
}
