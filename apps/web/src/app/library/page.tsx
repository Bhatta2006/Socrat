'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, Building2, ChevronLeft, ChevronRight, Filter, Search, Sparkles, Star, X } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard } from '@/lib/session';
import { conceptHref } from '@/lib/routes';
import type { Level as PracticeLevel, LibraryProblem, Recommendations } from '@/lib/types';
import { cn } from '@/lib/utils';
import { BandBadge, ErrorNote, Loading, Page, PageHeader, Reveal } from '@/components/common';
import { Level, LevelCard, PlatformTag, ProblemName, StatusControl } from '@/components/practice';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';
import { InputGroup, InputGroupAddon, InputGroupInput } from '@/components/ui/input-group';
import { NativeSelect, NativeSelectOptGroup, NativeSelectOption } from '@/components/ui/native-select';
import { Skeleton } from '@/components/ui/skeleton';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface Meta {
  platforms: Record<string, number>;
  sheets: Record<string, number>;
  concepts: { id: string; title: string; course: string; problems: number }[];
}
interface PageData { total: number; items: LibraryProblem[]; level: PracticeLevel }

const PLATFORMS = ['LeetCode', 'CSES', 'Codeforces'] as const;
const STATUSES = [
  ['all', 'All'],
  ['unsolved', 'Unsolved'],
  ['bookmarked', 'My list'],
  ['attempted', 'Attempted'],
  ['solved', 'Solved'],
] as const;
const SORTS = [
  ['recommended', 'Best for me'],
  ['easiest', 'Easiest first'],
  ['hardest', 'Hardest first'],
  ['popular', 'Most asked'],
  ['title', 'A–Z'],
] as const;
const RATINGS = Array.from({ length: 28 }, (_, i) => 800 + i * 100);
const PAGE = 30;

type Filters = {
  q: string;
  platform: string[];
  concept: string;
  difficulty: string;
  rating_min: number;
  rating_max: number;
  sheet: string;
  status: (typeof STATUSES)[number][0];
  sort: (typeof SORTS)[number][0];
};
const EMPTY: Filters = { q: '', platform: [], concept: '', difficulty: '', rating_min: 0, rating_max: 0, sheet: '', status: 'all', sort: 'recommended' };

function fromLocation(): Filters {
  if (typeof window === 'undefined') return EMPTY;
  const params = new URLSearchParams(window.location.search);
  const status = params.get('status') ?? 'all';
  const sort = params.get('sort') ?? 'recommended';
  return {
    q: params.get('q') ?? '',
    platform: (params.get('platform') ?? '').split(',').filter(p => (PLATFORMS as readonly string[]).includes(p)),
    concept: params.get('concept') ?? '',
    difficulty: params.get('difficulty') ?? '',
    rating_min: Number(params.get('rating_min')) || 0,
    rating_max: Number(params.get('rating_max')) || 0,
    sheet: params.get('sheet') ?? '',
    status: (STATUSES.some(s => s[0] === status) ? status : 'all') as Filters['status'],
    sort: (SORTS.some(s => s[0] === sort) ? sort : 'recommended') as Filters['sort'],
  };
}

function query(f: Filters, offset = 0): string {
  const params = new URLSearchParams();
  if (f.q) params.set('q', f.q);
  if (f.platform.length) params.set('platform', f.platform.join(','));
  if (f.concept) params.set('concept', f.concept);
  if (f.difficulty) params.set('difficulty', f.difficulty);
  if (f.rating_min) params.set('rating_min', String(f.rating_min));
  if (f.rating_max) params.set('rating_max', String(f.rating_max));
  if (f.sheet) params.set('sheet', f.sheet);
  if (f.status !== 'all') params.set('status', f.status);
  if (f.sort !== 'recommended') params.set('sort', f.sort);
  if (offset) params.set('offset', String(offset));
  return params.toString();
}

export default function Library() {
  const allowed = useGuard('active');
  const [meta, setMeta] = useState<Meta | null>(null);
  const [recs, setRecs] = useState<Recommendations | null>(null);
  const [filters, setFilters] = useState<Filters | null>(null);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState<PageData | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const initial = fromLocation();
    setFilters(initial);
    setSearch(initial.q);
  }, []);
  useEffect(() => {
    if (!allowed) return;
    api.get<Meta>('/library/meta').then(setMeta).catch(e => setError(explain(e)));
    api.get<Recommendations>('/library/recommendations?limit=6').then(setRecs).catch(() => undefined);
  }, [allowed]);
  useEffect(() => {
    const timer = setTimeout(() => setFilters(f => (f && f.q !== search.trim() ? { ...f, q: search.trim() } : f)), 250);
    return () => clearTimeout(timer);
  }, [search]);

  const load = useCallback(() => {
    if (!allowed || !filters) return;
    setLoading(true);
    setError('');
    const qs = query(filters);
    window.history.replaceState(null, '', qs ? `/library?${qs}` : '/library');
    api.get<PageData>(`/library?${query(filters, offset)}&limit=${PAGE}`)
      .then(setPage)
      .catch(e => setError(explain(e)))
      .finally(() => setLoading(false));
  }, [allowed, filters, offset]);
  useEffect(load, [load]);

  const update = (patch: Partial<Filters>) => { setOffset(0); setFilters(f => (f ? { ...f, ...patch } : f)); };
  const replaceItem = (id: string, patch: Partial<LibraryProblem>) =>
    setPage(p => (p ? { ...p, items: p.items.map(i => (i.id === id ? { ...i, ...patch } : i)) } : p));

  const grouped = useMemo(() => {
    const groups: Record<string, Meta['concepts']> = {};
    for (const c of meta?.concepts ?? []) (groups[c.course] ??= []).push(c);
    return groups;
  }, [meta]);

  if (!allowed || !filters) return <Loading />;
  const total = meta ? Object.values(meta.platforms).reduce((a, b) => a + b, 0) : 0;
  const active = filters.q || filters.platform.length || filters.concept || filters.difficulty || filters.rating_min || filters.rating_max || filters.sheet;
  const conceptTitle = meta?.concepts.find(c => c.id === filters.concept)?.title;

  return (
    <Page wide>
      <Reveal>
        <PageHeader
          eyebrow="Practice"
          title="Practice library"
          description={<>{total ? `${total.toLocaleString()} problems` : 'Problems'} from LeetCode, CSES and Codeforces, each tied to a concept and ranked for where you are now.</>}
          actions={<Button asChild variant="outline"><Link href="/companies"><Building2 data-icon="inline-start" /> Company question bank</Link></Button>}
        />
      </Reveal>

      {recs ? (
        <Reveal index={1} className="mb-8 grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)]">
          <Card>
            <CardContent className="grid gap-4">
              <LevelCard level={recs.level} solved={recs.solved_external} />
              <p className="text-xs text-muted-foreground">Your level comes from your mastery{recs.codeforces ? ' and your Codeforces rating' : ''}. Solve problems and it rises.</p>
              {!recs.codeforces ? (
                <Button asChild variant="secondary" size="sm" className="w-fit"><Link href="/settings#codeforces">Link Codeforces for sharper picks</Link></Button>
              ) : null}
            </CardContent>
          </Card>
          <Card aria-labelledby="for-you-heading">
            <CardHeader>
              <CardTitle id="for-you-heading" className="flex items-center gap-2"><Sparkles className="size-4 text-primary" /> Recommended for you</CardTitle>
              <CardDescription>Picked from your mastery, refreshed daily</CardDescription>
            </CardHeader>
            <CardContent>
              {recs.problems.length ? (
                <ul className="grid gap-2 md:grid-cols-2">
                  {recs.problems.map(p => (
                    <li key={p.id} className="min-w-0 rounded-lg border p-3 transition-colors hover:border-primary/40 hover:bg-muted/30">
                      <div className="flex flex-wrap items-center gap-2">
                        <ProblemName problem={p} />
                        <PlatformTag platform={p.platform} />
                        <Level problem={p} />
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{p.reason}</p>
                    </li>
                  ))}
                </ul>
              ) : <p className="text-sm text-muted-foreground">Finish your first lesson and we&apos;ll start picking problems for you.</p>}
            </CardContent>
          </Card>
        </Reveal>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside aria-label="Filters" className="lg:sticky lg:top-20 lg:self-start">
          <Card size="sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2"><Filter className="size-3.5" /> Filters</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-5">
              <InputGroup>
                <InputGroupAddon><Search /></InputGroupAddon>
                <InputGroupInput placeholder="Problem name" value={search} onChange={e => setSearch(e.target.value)} aria-label="Search problems" />
              </InputGroup>
              <fieldset>
                <legend className="mb-2 text-xs font-medium text-muted-foreground">Platform</legend>
                <div className="flex flex-wrap gap-1.5">
                  {PLATFORMS.map(p => {
                    const on = filters.platform.includes(p);
                    return (
                      <button
                        key={p}
                        type="button"
                        aria-pressed={on}
                        className={cn('inline-flex h-7 items-center gap-1 rounded-full border px-2.5 text-xs font-medium transition-colors hover:border-primary/50', on && 'border-primary bg-primary/10 text-primary')}
                        onClick={() => update({ platform: on ? filters.platform.filter(x => x !== p) : [...filters.platform, p] })}
                      >
                        {p}{meta?.platforms[p] ? <span className="text-muted-foreground tabular-nums">{meta.platforms[p].toLocaleString()}</span> : null}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
              <label className="grid gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">Concept</span>
                <NativeSelect className="w-full" value={filters.concept} onChange={e => update({ concept: e.target.value })}>
                  <NativeSelectOption value="">Any concept</NativeSelectOption>
                  {Object.entries(grouped).map(([course, concepts]) => (
                    <NativeSelectOptGroup key={course} label={course}>
                      {concepts.map(c => <NativeSelectOption key={c.id} value={c.id}>{c.title} ({c.problems})</NativeSelectOption>)}
                    </NativeSelectOptGroup>
                  ))}
                </NativeSelect>
              </label>
              <label className="grid gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">Difficulty</span>
                <NativeSelect className="w-full" value={filters.difficulty} onChange={e => update({ difficulty: e.target.value })}>
                  <NativeSelectOption value="">Any</NativeSelectOption>
                  <NativeSelectOption value="easy">Easy</NativeSelectOption>
                  <NativeSelectOption value="medium">Medium</NativeSelectOption>
                  <NativeSelectOption value="hard">Hard</NativeSelectOption>
                </NativeSelect>
              </label>
              <fieldset>
                <legend className="mb-1.5 text-xs font-medium text-muted-foreground">Rating</legend>
                <div className="flex items-center gap-2">
                  <NativeSelect className="min-w-0 flex-1" aria-label="Minimum rating" value={filters.rating_min} onChange={e => update({ rating_min: Number(e.target.value) })}>
                    <NativeSelectOption value={0}>Min</NativeSelectOption>
                    {RATINGS.map(r => <NativeSelectOption key={r} value={r}>{r}</NativeSelectOption>)}
                  </NativeSelect>
                  <span className="text-muted-foreground">–</span>
                  <NativeSelect className="min-w-0 flex-1" aria-label="Maximum rating" value={filters.rating_max} onChange={e => update({ rating_max: Number(e.target.value) })}>
                    <NativeSelectOption value={0}>Max</NativeSelectOption>
                    {RATINGS.map(r => <NativeSelectOption key={r} value={r}>{r}</NativeSelectOption>)}
                  </NativeSelect>
                </div>
                <p className="mt-1.5 text-xs text-muted-foreground">Codeforces ratings; other sites are placed on the same scale.</p>
              </fieldset>
              {meta?.sheets['striver-a2z'] ? (
                <label className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox checked={filters.sheet === 'striver-a2z'} onCheckedChange={v => update({ sheet: v === true ? 'striver-a2z' : '' })} />
                  On the Striver A2Z sheet
                </label>
              ) : null}
              {active ? (
                <Button type="button" variant="ghost" size="sm" onClick={() => { setSearch(''); update({ ...EMPTY, status: filters.status, sort: filters.sort }); }}>
                  <X data-icon="inline-start" /> Clear filters
                </Button>
              ) : null}
            </CardContent>
          </Card>
        </aside>

        <section className="min-w-0" aria-labelledby="results-heading">
          <h2 id="results-heading" className="sr-only">Problems</h2>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <Tabs value={filters.status} onValueChange={v => update({ status: v as Filters['status'] })}>
              <TabsList>
                {STATUSES.map(([id, label]) => (
                  <TabsTrigger key={id} value={id}>{id === 'bookmarked' ? <Star className="size-3.5" /> : null}{label}</TabsTrigger>
                ))}
              </TabsList>
            </Tabs>
            <label className="flex items-center gap-2 text-sm">
              <span className="text-muted-foreground">Sort</span>
              <NativeSelect value={filters.sort} onChange={e => update({ sort: e.target.value as Filters['sort'] })}>
                {SORTS.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
              </NativeSelect>
            </label>
          </div>
          {active ? (
            <div className="mb-3 flex flex-wrap items-center gap-1.5 text-xs">
              <span className="text-muted-foreground">{page ? `${page.total.toLocaleString()} results` : 'Filtering'}</span>
              {filters.q ? <Badge variant="secondary">“{filters.q}”</Badge> : null}
              {filters.platform.map(p => <Badge key={p} variant="secondary">{p}</Badge>)}
              {conceptTitle ? <Badge variant="secondary">{conceptTitle}</Badge> : null}
              {filters.difficulty ? <Badge variant="secondary" className="capitalize">{filters.difficulty}</Badge> : null}
              {filters.rating_min || filters.rating_max ? <Badge variant="secondary">{filters.rating_min || 'any'}–{filters.rating_max || 'any'}</Badge> : null}
            </div>
          ) : null}
          <Card className="gap-0 overflow-hidden py-0" aria-busy={loading}>
            <Table>
              <TableHeader className="bg-muted/40">
                <TableRow>
                  <TableHead className="pl-4">Problem</TableHead>
                  <TableHead>Level</TableHead>
                  <TableHead className="hidden md:table-cell">Concept</TableHead>
                  <TableHead className="pr-4 text-right">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className={cn('transition-opacity', loading && 'opacity-60')}>
                {page?.items.map(p => (
                  <TableRow key={p.id} className={cn(p.status === 'solved' && 'bg-success/5')}>
                    <TableCell className="min-w-56 py-3 pl-4 whitespace-normal">
                      <div className="flex flex-wrap items-center gap-2">
                        <ProblemName problem={p} onOpened={() => replaceItem(p.id, { status: p.status ?? 'attempted' })} />
                        <PlatformTag platform={p.platform} />
                        {p.striver ? <Badge variant="secondary">A2Z</Badge> : null}
                      </div>
                      {p.companies ? <p className="mt-0.5 text-xs text-muted-foreground">Asked at {p.companies} companies</p> : null}
                    </TableCell>
                    <TableCell><Level problem={p} /></TableCell>
                    <TableCell className="hidden min-w-44 md:table-cell">
                      {p.concept ? (
                        <Link href={conceptHref(p.concept.id)} className="grid gap-0.5 hover:text-primary">
                          <span className="text-sm">{p.concept.title}</span>
                          <BandBadge band={p.concept.band} />
                        </Link>
                      ) : null}
                    </TableCell>
                    <TableCell className="pr-4 text-right">
                      <StatusControl id={p.id} status={p.status} bookmarked={p.bookmarked} compact onChange={next => replaceItem(p.id, next)} />
                    </TableCell>
                  </TableRow>
                ))}
                {!page ? Array.from({ length: 8 }, (_, i) => (
                  <TableRow key={`s${i}`}><TableCell colSpan={4} className="px-4"><Skeleton className="h-6 w-full" /></TableCell></TableRow>
                )) : null}
              </TableBody>
            </Table>
            {page && !page.items.length ? (
              <Empty className="border-0 py-12">
                <EmptyHeader>
                  <EmptyMedia variant="icon">{filters.status === 'bookmarked' ? <Star /> : <Search />}</EmptyMedia>
                  <EmptyTitle>{filters.status === 'bookmarked' ? 'Your list is empty' : 'No problems match'}</EmptyTitle>
                  <EmptyDescription>{filters.status === 'bookmarked' ? 'Star a problem to save it here.' : 'Try widening the rating range or clearing a filter.'}</EmptyDescription>
                </EmptyHeader>
              </Empty>
            ) : null}
          </Card>
          {page && page.total > PAGE ? (
            <div className="mt-4 flex items-center justify-between text-sm">
              <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - PAGE))}><ChevronLeft data-icon="inline-start" /> Previous</Button>
              <span className="text-muted-foreground tabular-nums">{offset + 1}–{Math.min(offset + PAGE, page.total)} of {page.total.toLocaleString()}</span>
              <Button variant="outline" size="sm" disabled={offset + PAGE >= page.total} onClick={() => setOffset(o => o + PAGE)}>Next <ChevronRight data-icon="inline-end" /></Button>
            </div>
          ) : null}
          {error ? <ErrorNote message={error} retry={load} /> : null}
          <p className="mt-4 flex items-center gap-1 text-xs text-muted-foreground">
            Names, ratings and tags only — statements stay on the original sites. <ArrowRight className="size-3" /> Mark problems solved here, or link Codeforces to sync.
          </p>
        </section>
      </div>
    </Page>
  );
}
