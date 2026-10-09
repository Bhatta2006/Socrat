'use client';

import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { Building2, ChevronLeft, ChevronRight, Search } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { conceptHref } from '@/lib/routes';
import type { CompanyProblem } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BandBadge, Difficulty, ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { ProblemName } from '@/components/practice';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';

interface Company { slug: string; name: string; problems: number }
interface CompanyView { slug: string; name: string; total: number; items: CompanyProblem[] }

const WINDOWS = [
  ['thirty-days', 'Last 30 days'],
  ['three-months', 'Last 3 months'],
  ['six-months', 'Last 6 months'],
  ['all', 'All time'],
] as const;
const PAGE = 50;

export default function Companies() {
  const allowed = useGuard('active');
  const [query, setQuery] = useState('');
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [selected, setSelected] = useState<string>('');
  const [range, setRange] = useState<(typeof WINDOWS)[number][0]>('three-months');
  const [difficulty, setDifficulty] = useState<'all' | 'easy' | 'medium' | 'hard'>('all');
  const [view, setView] = useState<CompanyView | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!allowed) return;
    const timer = setTimeout(() => {
      api.get<{ items: Company[] }>(`/companies?q=${encodeURIComponent(query)}&limit=60`)
        .then(r => { setCompanies(r.items); setSelected(s => s || r.items[0]?.slug || ''); })
        .catch(e => setError(explain(e)));
    }, 200);
    return () => clearTimeout(timer);
  }, [allowed, query]);

  const load = useCallback(() => {
    if (!selected) return;
    setError('');
    api.get<CompanyView>(`/companies/${selected}?window=${range}&difficulty=${difficulty}&offset=${offset}&limit=${PAGE}`)
      .then(setView)
      .catch(e => setError(explain(e)));
  }, [selected, range, difficulty, offset]);
  useEffect(load, [load]);

  if (!allowed || !companies) return <Loading />;

  return (
    <Page wide>
      <PageHeader
        eyebrow="Interview prep"
        title="Company question bank"
        description="Problems reported in recent interviews, ordered by how often they come up. Each shows the concept it practises and where you stand on it — learn the concept first, then come back."
      />

      <div className="grid gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
        <Card size="sm" className="h-fit lg:sticky lg:top-20">
          <CardContent className="grid gap-3">
            <InputGroup>
              <InputGroupAddon><Search /></InputGroupAddon>
              <InputGroupInput placeholder="Search companies" aria-label="Search companies" value={query} onChange={e => setQuery(e.target.value)} />
            </InputGroup>
            <ScrollArea className="h-[60vh]">
              <ul className="grid gap-0.5 pr-2">
                {companies.map(c => (
                  <li key={c.slug}>
                    <button
                      type="button"
                      className={cn('flex w-full items-center justify-between gap-2 rounded-md px-2.5 py-2 text-left text-sm transition-colors hover:bg-muted', selected === c.slug && 'bg-primary/10 font-medium text-primary')}
                      aria-pressed={selected === c.slug}
                      onClick={() => { setSelected(c.slug); setOffset(0); }}
                    >
                      <span className="flex min-w-0 items-center gap-2"><Building2 className="size-3.5 flex-none opacity-60" /><span className="truncate">{c.name}</span></span>
                      <span className="text-xs text-muted-foreground tabular-nums">{c.problems}</span>
                    </button>
                  </li>
                ))}
                {!companies.length ? <li className="px-3 py-2 text-sm text-muted-foreground">No companies match.</li> : null}
              </ul>
            </ScrollArea>
          </CardContent>
        </Card>

        <section className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold tracking-tight">
              {view?.name ?? 'Loading…'} {view ? <span className="text-sm font-normal text-muted-foreground">· {view.total} problems</span> : null}
            </h2>
            <div className="flex flex-wrap gap-2">
              <NativeSelect value={range} onChange={e => { setRange(e.target.value as typeof range); setOffset(0); }} aria-label="Time window">
                {WINDOWS.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
              </NativeSelect>
              <NativeSelect value={difficulty} onChange={e => { setDifficulty(e.target.value as typeof difficulty); setOffset(0); }} aria-label="Difficulty">
                <NativeSelectOption value="all">Any difficulty</NativeSelectOption>
                <NativeSelectOption value="easy">Easy</NativeSelectOption>
                <NativeSelectOption value="medium">Medium</NativeSelectOption>
                <NativeSelectOption value="hard">Hard</NativeSelectOption>
              </NativeSelect>
            </div>
          </div>
          <Card className="gap-0 overflow-hidden py-0">
            <Table>
              <TableHeader className="bg-muted/40">
                <TableRow>
                  <TableHead className="pl-4">Problem</TableHead>
                  <TableHead>Difficulty</TableHead>
                  <TableHead>Frequency</TableHead>
                  <TableHead className="pr-4">Concept</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {view?.items.map(p => (
                  <TableRow key={p.id}>
                    <TableCell className="min-w-56 py-3 pl-4 whitespace-normal">
                      <span className="flex flex-wrap items-center gap-2">
                        <ProblemName problem={p} />
                        {p.striver ? <Badge variant="secondary">A2Z</Badge> : null}
                      </span>
                    </TableCell>
                    <TableCell><Difficulty level={p.difficulty} /></TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <span className="relative h-1.5 w-16 overflow-hidden rounded-full bg-muted" aria-label={`Frequency ${p.frequency}%`}>
                          <span className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${p.frequency}%` }} />
                        </span>
                        <span className="text-xs text-muted-foreground tabular-nums">{Math.round(p.frequency)}%</span>
                      </div>
                    </TableCell>
                    <TableCell className="min-w-48 pr-4">
                      {p.concept ? (
                        <Link href={conceptHref(p.concept.id)} className="grid gap-0.5 hover:text-primary">
                          <span className="text-sm">{p.concept.title}</span>
                          <BandBadge band={p.concept.band} />
                        </Link>
                      ) : <span className="text-xs text-muted-foreground">—</span>}
                    </TableCell>
                  </TableRow>
                ))}
                {!view ? Array.from({ length: 8 }, (_, i) => (
                  <TableRow key={`s${i}`}><TableCell colSpan={4} className="px-4"><Skeleton className="h-6 w-full" /></TableCell></TableRow>
                )) : null}
                {view && !view.items.length ? (
                  <TableRow><TableCell colSpan={4} className="py-10 text-center text-muted-foreground">No problems in this window. Try a longer time range.</TableCell></TableRow>
                ) : null}
              </TableBody>
            </Table>
          </Card>
          {view && view.total > PAGE ? (
            <div className="mt-4 flex items-center justify-between text-sm">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - PAGE))}><ChevronLeft data-icon="inline-start" /> Previous</Button>
              <span className="text-muted-foreground tabular-nums">{offset + 1}–{Math.min(offset + PAGE, view.total)} of {view.total}</span>
              <Button variant="outline" size="sm" disabled={offset + PAGE >= view.total} onClick={() => setOffset(o => o + PAGE)}>Next <ChevronRight data-icon="inline-end" /></Button>
            </div>
          ) : null}
          {error ? <ErrorNote message={error} retry={load} /> : null}
          <p className="mt-4 text-xs text-muted-foreground">Company frequency data: community-maintained LeetCode snapshots. Problems open on LeetCode.</p>
        </section>
      </div>
    </Page>
  );
}
