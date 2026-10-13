'use client';

import { useEffect, useState } from 'react';
import { Activity, Gauge, MessageSquare, ShieldAlert, ThumbsUp, Users } from 'lucide-react';
import { ApiError, api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { ErrorNote, Loading, Page, PageHeader, StatCard } from '@/components/common';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Overview {
  funnel: { step: string; learners: number; share: number }[];
  activation: { activated: number; signups: number; rate: number };
  retention: { day: number; eligible: number; retained: number; rate: number | null }[];
  engagement: {
    weekly_active: number;
    minutes_per_active_day: number;
    tutor_messages_7d: number;
    tutor_messages_per_active: number;
    tutor_ratings: { up: number; down: number };
  };
  gates: { module: string; learners: number; pass_rate: number; attempts_per_learner: number }[];
  flagged_items: { concept: string; item: string; answers: number; correct_rate: number; issue: string }[];
  unhelpful_resources: { concept: string; url: string; opens: number; helpful: number; unhelpful: number }[];
}

const pct = (v: number | null) => (v === null ? '—' : `${Math.round(v * 100)}%`);

/** Single-series horizontal bars: magnitude by length, every value labelled, no legend needed. */
function Funnel({ steps }: { steps: Overview['funnel'] }) {
  const max = Math.max(1, ...steps.map(s => s.learners));
  return (
    <ol className="grid gap-2.5" aria-label="Activation funnel">
      {steps.map(s => (
        <li key={s.step} className="group grid grid-cols-[180px_minmax(0,1fr)_96px] items-center gap-3 text-sm" title={`${s.step}: ${s.learners} learners (${pct(s.share)} of sign-ups)`}>
          <span className="truncate text-muted-foreground">{s.step}</span>
          <span className="relative h-5">
            <span
              className="absolute inset-y-0 left-0 rounded-r-[4px] bg-primary transition-opacity group-hover:opacity-80"
              style={{ width: `${Math.max(1, (100 * s.learners) / max)}%` }}
            />
          </span>
          <span className="text-right tabular-nums">
            <span className="font-medium">{s.learners.toLocaleString()}</span>{' '}
            <span className="text-xs text-muted-foreground">{pct(s.share)}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export default function Admin() {
  const allowed = useGuard('signed-in');
  const [data, setData] = useState<Overview | null>(null);
  const [forbidden, setForbidden] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!allowed) return;
    api.get<Overview>('/admin/overview')
      .then(setData)
      .catch(e => (e instanceof ApiError && e.status === 403 ? setForbidden(true) : setError(explain(e))));
  }, [allowed]);

  if (forbidden) {
    return (
      <Page narrow>
        <Empty className="mt-16">
          <EmptyHeader>
            <EmptyMedia variant="icon"><ShieldAlert /></EmptyMedia>
            <EmptyTitle>Admin access only</EmptyTitle>
            <EmptyDescription>Add your account to SOCRAT_ADMIN_SUBJECTS on the server to see owner metrics.</EmptyDescription>
          </EmptyHeader>
        </Empty>
      </Page>
    );
  }
  if (!allowed || (!data && !error)) return <Loading />;
  if (!data) return <Page><ErrorNote message={error} /></Page>;

  const e = data.engagement;
  return (
    <Page wide>
      <PageHeader eyebrow="Owner" title="How learners are doing" description="Computed from learning data. No third-party tracking." />

      <div className="mb-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={<Gauge />} label="Activation (lesson + check within 24 h)" value={pct(data.activation.rate)} hint={`${data.activation.activated} of ${data.activation.signups} sign-ups`} />
        <StatCard icon={<Users />} label="Weekly active learners" value={e.weekly_active.toLocaleString()} hint={`${e.minutes_per_active_day} min per active day`} />
        <StatCard icon={<MessageSquare />} label="Tutor messages, last 7 days" value={e.tutor_messages_7d.toLocaleString()} hint={`${e.tutor_messages_per_active} per active learner`} />
        <StatCard icon={<ThumbsUp />} label="Tutor reply ratings" value={`${e.tutor_ratings.up} / ${e.tutor_ratings.down}`} hint="helpful / not helpful" />
      </div>

      <div className="mb-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Card>
          <CardHeader><CardTitle>Activation funnel</CardTitle><CardDescription>Learners reaching each step, share of all sign-ups</CardDescription></CardHeader>
          <CardContent><Funnel steps={data.funnel} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Activity className="size-4 text-primary" /> Retention</CardTitle><CardDescription>Studied on day N after sign-up</CardDescription></CardHeader>
          <CardContent className="grid grid-cols-3 gap-3">
            {data.retention.map(r => (
              <div key={r.day} className="rounded-lg border p-3 text-center">
                <p className="text-xs text-muted-foreground">D{r.day}</p>
                <p className="text-2xl font-semibold tabular-nums">{pct(r.rate)}</p>
                <p className="text-[11px] text-muted-foreground">{r.retained}/{r.eligible}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Checkpoints</CardTitle><CardDescription>Hardest first; a very low pass rate may mean missing teaching</CardDescription></CardHeader>
          {data.gates.length ? (
            <Table>
              <TableHeader><TableRow><TableHead className="pl-4">Module</TableHead><TableHead className="text-right">Learners</TableHead><TableHead className="text-right">Pass rate</TableHead><TableHead className="pr-4 text-right">Attempts each</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.gates.map(g => (
                  <TableRow key={g.module}>
                    <TableCell className="pl-4">{g.module}</TableCell>
                    <TableCell className="text-right tabular-nums">{g.learners}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(g.pass_rate)}</TableCell>
                    <TableCell className="pr-4 text-right tabular-nums">{g.attempts_per_learner}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <CardContent className="pb-6 text-sm text-muted-foreground">No checkpoint attempts yet.</CardContent>}
        </Card>
        <Card className="gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Questions to review</CardTitle><CardDescription>At least 20 answers and nearly everyone right, or nearly everyone wrong</CardDescription></CardHeader>
          {data.flagged_items.length ? (
            <Table>
              <TableHeader><TableRow><TableHead className="pl-4">Concept · item</TableHead><TableHead className="text-right">Answers</TableHead><TableHead className="text-right">Correct</TableHead><TableHead className="pr-4">Issue</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.flagged_items.map(i => (
                  <TableRow key={`${i.concept}-${i.item}`}>
                    <TableCell className="pl-4 whitespace-normal">{i.concept} · <span className="font-mono text-xs">{i.item}</span></TableCell>
                    <TableCell className="text-right tabular-nums">{i.answers}</TableCell>
                    <TableCell className="text-right tabular-nums">{pct(i.correct_rate)}</TableCell>
                    <TableCell className="pr-4">{i.issue}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : <CardContent className="pb-6 text-sm text-muted-foreground">Nothing flagged yet — items need 20+ answers to judge.</CardContent>}
        </Card>
      </div>

      {data.unhelpful_resources.length ? (
        <Card className="mt-6 gap-0 overflow-hidden pb-0">
          <CardHeader className="pb-3"><CardTitle>Resources learners found unhelpful</CardTitle></CardHeader>
          <Table>
            <TableHeader><TableRow><TableHead className="pl-4">Concept</TableHead><TableHead>Link</TableHead><TableHead className="text-right">Opens</TableHead><TableHead className="pr-4 text-right">Helpful / not</TableHead></TableRow></TableHeader>
            <TableBody>
              {data.unhelpful_resources.map(r => (
                <TableRow key={`${r.concept}-${r.url}`}>
                  <TableCell className="pl-4">{r.concept}</TableCell>
                  <TableCell className="max-w-80 truncate"><a href={r.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{r.url}</a></TableCell>
                  <TableCell className="text-right tabular-nums">{r.opens}</TableCell>
                  <TableCell className="pr-4 text-right tabular-nums">{r.helpful} / {r.unhelpful}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      ) : null}
    </Page>
  );
}
