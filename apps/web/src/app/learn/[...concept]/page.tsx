'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { motion, useScroll, useSpring } from 'motion/react';
import { AlertTriangle, ArrowRight, BookMarked, CheckCircle2, Code2, ExternalLink, Lightbulb, ListChecks, Sparkles, Wand2 } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { activityHref, conceptHref, joinSegments } from '@/lib/routes';
import type { ConceptView } from '@/lib/types';
import Markdown from '@/components/markdown';
import Assistant from '@/components/assistant';
import { BackLink, BandBadge, Difficulty, ErrorNote, Loading } from '@/components/common';
import { Level, PlatformTag, ProblemName, StatusControl } from '@/components/practice';
import { celebrate } from '@/components/celebrate';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';

const STYLES = [
  ['simpler', 'Explain it more simply'],
  ['example', 'Show another example'],
  ['deeper', 'Go deeper'],
] as const;

function ReadingProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 140, damping: 30 });
  return <motion.div className="fixed inset-x-0 top-0 z-50 h-0.5 origin-left bg-primary" style={{ scaleX }} aria-hidden="true" />;
}

export default function Lesson() {
  const allowed = useGuard('signed-in');
  const { profile } = useSession();
  const params = useParams<{ concept: string[] }>();
  const qualified = joinSegments(params.concept);
  const [concept, setConcept] = useState<ConceptView | null>(null);
  const [error, setError] = useState('');
  const [variant, setVariant] = useState<{ style: string; content: string } | null>(null);
  const [explaining, setExplaining] = useState('');
  const [completing, setCompleting] = useState(false);
  const active = profile?.enrollment?.status === 'active';

  const load = useCallback(() => {
    setError('');
    api.get<ConceptView>(`/concepts/${qualified}`).then(setConcept).catch(e => setError(explain(e)));
  }, [qualified]);
  useEffect(() => {
    if (!allowed) return;
    load();
    if (active) api.post(`/activities/lesson:${qualified}/start`).catch(() => undefined);
  }, [allowed, active, load, qualified]);

  async function reexplain(style: string) {
    setExplaining(style);
    try {
      const result = await api.post<{ content: string }>(`/concepts/${qualified}/explain`, { style });
      setVariant({ style, content: result.content });
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setExplaining('');
    }
  }

  async function complete() {
    setCompleting(true);
    try {
      await api.post(`/activities/lesson:${qualified}/complete`);
      setConcept(c => (c ? { ...c, lesson_done: true } : c));
      celebrate('small');
      toast.success('Lesson complete', { description: 'Lock it in with the concept check.' });
    } catch (e) {
      setError(explain(e));
    } finally {
      setCompleting(false);
    }
  }

  if (!allowed || (!concept && !error)) return <Loading />;
  if (!concept) return <div className="mx-auto max-w-3xl p-6"><ErrorNote message={error} retry={load} /></div>;

  const weakPrereqs = concept.prerequisites.filter(p => p.band === 'needs_practice' || p.band === 'not_started');
  const practice = [
    ...concept.practice_links.map(p => ({
      id: p.url, title: p.title, url: p.url, platform: p.platform, difficulty: p.difficulty, rating: null,
      concepts: [] as string[], companies: 0, striver: false, status: null, bookmarked: false, concept: null,
    })),
    ...concept.more_practice,
  ]
    .filter((p, i, all) => all.findIndex(q => q.url.replace(/\/$/, '') === p.url.replace(/\/$/, '')) === i)
    .slice(0, 10);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pt-6 pb-28 sm:px-6 md:pt-8">
      <ReadingProgress />
      <BackLink href="/today">Today</BackLink>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_300px]">
        <article className="min-w-0">
          <header className="mb-8">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge variant="secondary" className="gap-1"><BookMarked className="size-3" /> Lesson</Badge>
              <BandBadge band={concept.band} />
              {concept.lesson_done ? <Badge variant="outline" className="gap-1 border-success/30 bg-success/10 text-success"><CheckCircle2 className="size-3" /> Completed</Badge> : null}
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-balance md:text-5xl">{concept.title}</h1>
            <p className="mt-3 text-lg text-muted-foreground text-pretty">{concept.summary}</p>
          </header>

          {weakPrereqs.length ? (
            <Alert className="mb-6 border-warning/40 bg-warning/10">
              <AlertTriangle className="text-warning" />
              <AlertDescription>
                <span>
                  This builds on{' '}
                  {weakPrereqs.map((p, i, all) => (
                    <span key={p.id}><Link className="font-medium underline underline-offset-2" href={conceptHref(p.id)}>{p.title}</Link>{i < all.length - 1 ? ', ' : ''}</span>
                  ))}
                  . A quick look there first may help.
                </span>
              </AlertDescription>
            </Alert>
          ) : null}

          <Card>
            <CardContent className="py-2 md:px-8 md:py-4">
              <Markdown source={concept.lesson} language={concept.language} />
            </CardContent>
          </Card>

          <section className="mt-6" aria-labelledby="reexplain-heading">
            <h2 id="reexplain-heading" className="mb-3 flex items-center gap-2 text-sm font-medium"><Wand2 className="size-4 text-primary" /> Not clicking yet?</h2>
            <div className="flex flex-wrap gap-2">
              {STYLES.map(([style, label]) => (
                <Button key={style} type="button" variant={variant?.style === style ? 'secondary' : 'outline'} size="sm" aria-pressed={variant?.style === style} disabled={Boolean(explaining)} onClick={() => reexplain(style)}>
                  {explaining === style ? <Spinner /> : null}
                  {label}
                </Button>
              ))}
            </div>
            {variant ? (
              <Card className="mt-4 border-l-4 border-l-primary animate-in fade-in slide-in-from-bottom-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-sm"><Sparkles className="size-4 text-primary" /> {STYLES.find(s => s[0] === variant.style)?.[1]}</CardTitle>
                  <CardAction><Button variant="ghost" size="xs" onClick={() => setVariant(null)}>Hide</Button></CardAction>
                </CardHeader>
                <CardContent><Markdown source={variant.content} language={concept.language} /></CardContent>
              </Card>
            ) : null}
          </section>

          <Card className="mt-8 overflow-hidden" aria-labelledby="finish-heading">
            <CardContent className="flex flex-wrap items-center justify-between gap-4">
              {concept.lesson_done ? (
                <>
                  <div className="flex items-center gap-3">
                    <span className="grid size-10 place-items-center rounded-full bg-success/15 text-success"><CheckCircle2 className="size-5" /></span>
                    <div>
                      <h2 id="finish-heading" className="font-semibold">Lesson complete</h2>
                      <p className="text-sm text-muted-foreground">Check your understanding — a short quiz updates your mastery and your plan.</p>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {active ? (
                      <Button asChild><Link href={activityHref(`quiz:${concept.id}`)}><ListChecks data-icon="inline-start" /> {concept.quiz_done ? 'Retake the concept check' : 'Take the concept check'}</Link></Button>
                    ) : null}
                    <Button asChild variant="ghost"><Link href="/today">Back to today</Link></Button>
                  </div>
                </>
              ) : (
                <>
                  <div>
                    <h2 id="finish-heading" className="font-semibold">Finished reading?</h2>
                    <p className="text-sm text-muted-foreground">Mark it done, then take the concept check.</p>
                  </div>
                  <Button size="lg" className="h-10 px-5" disabled={!active || completing} onClick={complete}>
                    {completing ? <><Spinner /> Saving…</> : <><CheckCircle2 data-icon="inline-start" /> Mark lesson complete</>}
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          {practice.length ? (
            <Card className="mt-8" aria-labelledby="more-practice-heading">
              <CardHeader>
                <CardTitle id="more-practice-heading" className="text-base font-semibold">Practice more</CardTitle>
                <CardDescription>Picked for your current level. External problems open on the original site.</CardDescription>
                <CardAction><Button asChild variant="ghost" size="sm"><Link href={`/library?concept=${concept.id}`}>All problems <ArrowRight data-icon="inline-end" /></Link></Button></CardAction>
              </CardHeader>
              <CardContent>
                <ul className="grid divide-y">
                  {practice.map(p => (
                    <li key={p.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm">
                      <span className="flex min-w-0 flex-wrap items-center gap-2">
                        <ProblemName problem={p} />
                        <PlatformTag platform={p.platform} />
                        {p.striver ? <Badge variant="secondary">A2Z sheet</Badge> : null}
                      </span>
                      <span className="flex items-center gap-2">
                        <Level problem={p} />
                        {p.id.includes(':') && !p.id.startsWith('http') ? (
                          <StatusControl id={p.id} status={p.status} bookmarked={p.bookmarked} compact onChange={next => setConcept(c => (c ? { ...c, more_practice: c.more_practice.map(x => (x.id === p.id ? { ...x, ...next } : x)) } : c))} />
                        ) : null}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {error ? <ErrorNote message={error} /> : null}
        </article>

        <aside className="grid content-start gap-5 lg:sticky lg:top-20 lg:self-start">
          <Card size="sm">
            <CardHeader><CardTitle className="flex items-center gap-2"><Lightbulb className="size-4 text-primary" /> Remember</CardTitle></CardHeader>
            <CardContent>
              <ul className="grid gap-2.5 text-sm">
                {concept.key_points.map(p => <li key={p} className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 flex-none text-primary" /><span>{p}</span></li>)}
              </ul>
            </CardContent>
          </Card>
          {concept.pitfalls.length ? (
            <Card size="sm">
              <CardHeader><CardTitle className="flex items-center gap-2"><AlertTriangle className="size-4 text-warning" /> Common pitfalls</CardTitle></CardHeader>
              <CardContent>
                <ul className="grid gap-2.5 text-sm">
                  {concept.pitfalls.map(p => <li key={p} className="flex gap-2"><span className="mt-2 size-1.5 flex-none rounded-full bg-warning" /><span>{p}</span></li>)}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          {concept.problems.length ? (
            <Card size="sm">
              <CardHeader><CardTitle className="flex items-center gap-2"><Code2 className="size-4 text-primary" /> Practice problems</CardTitle></CardHeader>
              <CardContent>
                <ul className="-mx-2 grid">
                  {concept.problems.map(p => (
                    <li key={p.id}>
                      <Link href={`/problems/${p.id}`} className="flex items-center justify-between gap-2 rounded-md px-2 py-2 text-sm transition-colors hover:bg-muted">
                        <span className="flex items-center gap-2">{p.solved ? <CheckCircle2 className="size-4 text-success" /> : null}{p.title}</span>
                        <Difficulty level={p.difficulty} />
                      </Link>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          ) : null}
          <Card size="sm">
            <CardHeader><CardTitle>Go further</CardTitle></CardHeader>
            <CardContent className="grid gap-4">
              <ul className="grid gap-3 text-sm">
                {concept.resources.map(r => (
                  <li key={r.url}>
                    <a href={r.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 font-medium text-primary hover:underline">{r.title} <ExternalLink className="size-3" /></a>
                    <div className="text-xs text-muted-foreground">{r.source} · {r.kind} · {r.minutes} min</div>
                  </li>
                ))}
              </ul>
              {concept.handbook.length ? (
                <div className="border-t pt-3">
                  <h3 className="mb-2 text-xs font-medium text-muted-foreground">Competitive Programmer&apos;s Handbook</h3>
                  <ul className="grid gap-2 text-sm">
                    {concept.handbook.map(h => (
                      <li key={h.url}>
                        <a href={h.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">§{h.chapter} {h.title}</a>
                        <span className="text-xs text-muted-foreground"> · p. {h.page}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
              {concept.implementations.length ? (
                <div className="border-t pt-3">
                  <h3 className="mb-2 text-xs font-medium text-muted-foreground">Reference implementations</h3>
                  <ul className="grid gap-2 text-sm">
                    {concept.implementations.map(i => (
                      <li key={i.url}><a href={i.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">{i.title}</a> <span className="text-xs text-muted-foreground">· TheAlgorithms</span></li>
                    ))}
                  </ul>
                  <p className="mt-2 text-xs text-muted-foreground">Read these after you&apos;ve solved a problem yourself.</p>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </aside>
      </div>
      <Assistant scope={`concept:${concept.id}`} title="Ask about this lesson" language={concept.language} />
    </div>
  );
}
