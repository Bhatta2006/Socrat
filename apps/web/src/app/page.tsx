'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'motion/react';
import {
  ArrowRight,
  BookOpen,
  Brain,
  CalendarCheck,
  CheckCircle2,
  Code2,
  Flame,
  Library,
  MessageCircleQuestion,
  Route,
  Sparkles,
  Target,
} from 'lucide-react';
import { api } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Course } from '@/lib/types';
import { LANGUAGE_LABEL } from '@/lib/routes';
import { Loading, NumberTicker, Ring } from '@/components/common';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const STEPS = [
  { icon: Target, title: 'Tell us where you are', body: 'Pick a course and your level. A short adaptive check skips what you already know.' },
  { icon: Route, title: 'Follow a plan that adapts', body: 'Each day gets a few lessons, checks and problems sized to the time you have.' },
  { icon: MessageCircleQuestion, title: 'Get unstuck the Socratic way', body: 'Your tutor asks the next good question instead of handing over answers.' },
];

const FEATURES = [
  { icon: Brain, title: 'Knows what you know', body: 'Every quiz, run and submission updates a mastery model. Your plan re-flows around it, every day.', wide: true },
  { icon: Code2, title: 'A real code editor', body: 'Write, run and submit in Python, C++ or Java against hidden tests — with instant, readable verdicts.' },
  { icon: MessageCircleQuestion, title: 'A tutor that teaches', body: 'Hints rise one level at a time as you work. The full answer waits until you have genuinely tried.' },
  { icon: Library, title: '13,000+ curated problems', body: 'LeetCode, CSES and Codeforces, each tied to a concept and ranked for your level.' },
  { icon: CalendarCheck, title: 'Fits your week', body: 'Choose minutes per day and study days. Miss one and the plan adjusts — nothing piles up.', wide: true },
];

const FAQ = [
  ['Do I need to know how to code?', 'No. The Programming from Zero course starts with your very first program, and every lesson comes in Python, C++ or Java.'],
  ['How is this different from a problem list?', 'A list tells you what exists. Socrat decides what you should do next — based on what you have shown you know — and teaches the idea before the problem.'],
  ['Will the tutor just give me the answer?', 'Not straight away. It asks questions and gives hints that grow more specific as you make real attempts. A full walkthrough unlocks once you have genuinely struggled.'],
  ['What if I miss a day?', 'Your plan re-flows around your schedule. Spaced reviews bring back what is fading, so nothing important slips.'],
];

/** A live-looking slice of the app for the hero: today's plan, a streak and a mastery bar. */
function Preview() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24, rotate: -1 }}
      animate={{ opacity: 1, y: 0, rotate: 0 }}
      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1], delay: 0.15 }}
      className="relative"
    >
      <div className="absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-tr from-primary/25 via-sky-400/15 to-transparent blur-2xl" aria-hidden="true" />
      <Card className="gap-0 overflow-hidden p-0 shadow-2xl shadow-primary/10">
        <div className="flex items-center gap-1.5 border-b bg-muted/40 px-4 py-2.5">
          <span className="size-2.5 rounded-full bg-rose-400/80" /><span className="size-2.5 rounded-full bg-amber-400/80" /><span className="size-2.5 rounded-full bg-emerald-400/80" />
          <span className="ml-3 text-xs text-muted-foreground">socrat · Today</span>
        </div>
        <div className="grid gap-4 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-muted-foreground">Up next · Lesson · 12 min</p>
              <p className="mt-1 text-lg font-semibold">Two pointers</p>
              <p className="mt-1 text-xs text-muted-foreground">Builds on sorting, which you nailed yesterday.</p>
              <span className="mt-3 inline-flex h-8 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground">Start lesson <ArrowRight className="size-3.5" /></span>
            </div>
            <Ring value={68} size={78} stroke={7} label={<span className="text-xs">31/45m</span>} />
          </div>
          <div className="grid gap-2 rounded-xl border p-3">
            {[
              ['Sorting', 92, 'Strong'],
              ['Binary search', 64, 'Developing'],
              ['Two pointers', 18, 'Needs practice'],
            ].map(([title, value, band]) => (
              <div key={title as string} className="grid grid-cols-[110px_1fr_auto] items-center gap-3 text-xs">
                <span className="font-medium">{title}</span>
                <Progress value={value as number} className="h-1.5" />
                <span className="text-muted-foreground">{band}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between rounded-xl border bg-streak/5 p-3 text-xs">
            <span className="flex items-center gap-2 font-medium"><Flame className="size-4 fill-current text-streak" /> 12-day streak</span>
            <span className="text-muted-foreground">Next: Problem solver · 72%</span>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}

export default function Home() {
  const { profile, loading } = useSession();
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? '/today');
  }, [loading, profile, router]);
  useEffect(() => {
    api.get<{ items: Course[] }>('/courses').then(r => setCourses(r.items)).catch(() => undefined);
  }, []);

  if (loading || profile) return <Loading />;
  const concepts = courses.reduce((n, c) => n + c.concept_count, 0);
  const problems = courses.reduce((n, c) => n + c.problem_count, 0);

  return (
    <div className="overflow-x-clip">
      <section className="relative">
        <div className="bg-grid absolute inset-0 -z-10 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_70%)]" aria-hidden="true" />
        <div className="mx-auto grid max-w-6xl items-center gap-12 px-4 pt-14 pb-20 sm:px-6 md:grid-cols-[1.05fr_1fr] md:pt-24 md:pb-28">
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
            <Badge variant="outline" className="mb-6 gap-1.5 rounded-full bg-background/60 px-3 py-1 backdrop-blur">
              <Sparkles className="size-3 text-primary" /> Your personal programming tutor
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tighter text-balance sm:text-5xl md:text-6xl">
              Learn to code by <span className="bg-gradient-to-r from-primary to-sky-500 bg-clip-text text-transparent">thinking</span>, not copying.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted-foreground text-pretty">
              Socrat builds a plan around your goal and your schedule, teaches each idea in Python, C++ or Java,
              and checks real understanding with quizzes and judged problems.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg" className="h-11 px-6 text-sm shadow-lg shadow-primary/25">
                <Link href="/login">Start learning — it&apos;s free <ArrowRight data-icon="inline-end" /></Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="h-11 px-6 text-sm">
                <a href="#courses">See courses</a>
              </Button>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
              {['Adaptive placement', 'Daily plan', 'Socratic hints'].map(x => (
                <li key={x} className="flex items-center gap-1.5"><CheckCircle2 className="size-4 text-primary" /> {x}</li>
              ))}
            </ul>
          </motion.div>
          <Preview />
        </div>
      </section>

      {courses.length ? (
        <section className="border-y bg-muted/30">
          <div className="mx-auto grid max-w-6xl grid-cols-2 gap-6 px-4 py-10 sm:px-6 md:grid-cols-4">
            {[
              [courses.length, 'courses'],
              [concepts, 'concepts taught'],
              [problems, 'judged problems'],
              [13889, 'curated practice problems'],
            ].map(([value, label]) => (
              <div key={label as string} className="text-center">
                <p className="text-3xl font-semibold tracking-tight"><NumberTicker value={value as number} /></p>
                <p className="mt-1 text-sm text-muted-foreground">{label}</p>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section id="how" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-20 sm:px-6">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-medium text-primary">How it works</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">From first line to confident problem solver</h2>
        </div>
        <ol className="mt-12 grid gap-4 md:grid-cols-3">
          {STEPS.map((step, index) => (
            <motion.li key={step.title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.08 }}>
              <Card className="h-full">
                <CardContent className="grid gap-3">
                  <div className="flex items-center justify-between">
                    <span className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary"><step.icon className="size-5" /></span>
                    <span className="font-mono text-sm text-muted-foreground">0{index + 1}</span>
                  </div>
                  <h3 className="text-base font-semibold">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.body}</p>
                </CardContent>
              </Card>
            </motion.li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="grid gap-4 md:grid-cols-3">
          {FEATURES.map((f, index) => (
            <motion.div key={f.title} className={f.wide ? 'md:col-span-2' : ''} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: index * 0.06 }}>
              <Card className="group h-full transition-shadow hover:shadow-lg hover:shadow-primary/5">
                <CardContent className="grid gap-3">
                  <span className="grid size-10 place-items-center rounded-xl border bg-background text-primary transition-transform group-hover:scale-105"><f.icon className="size-5" /></span>
                  <h3 className="text-base font-semibold">{f.title}</h3>
                  <p className="text-sm text-muted-foreground">{f.body}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </section>

      <section id="courses" className="scroll-mt-20 border-t bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
          <div className="max-w-2xl">
            <p className="text-sm font-medium text-primary">Courses</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">Three paths, one engine</h2>
            <p className="mt-3 text-muted-foreground">Start anywhere. Prerequisites from other courses are pulled in automatically when you need them.</p>
          </div>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {courses.map((course, index) => (
              <Card key={course.id} className="relative flex flex-col transition-all hover:-translate-y-0.5 hover:shadow-lg">
                <CardContent className="flex flex-1 flex-col gap-3">
                  <span className="grid size-10 place-items-center rounded-xl bg-primary/10 text-primary">
                    {index === 0 ? <BookOpen className="size-5" /> : index === 1 ? <Target className="size-5" /> : <Flame className="size-5" />}
                  </span>
                  <h3 className="text-lg font-semibold">{course.title}</h3>
                  <p className="text-sm text-muted-foreground">{course.tagline}</p>
                  <p className="text-sm">{course.description}</p>
                  <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
                    <Badge variant="secondary">{course.concept_count} concepts</Badge>
                    <Badge variant="secondary">{course.problem_count} problems</Badge>
                    <Badge variant="outline">{course.languages.map(l => LANGUAGE_LABEL[l]).join(' · ')}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
        <h2 className="text-center text-3xl font-semibold tracking-tight">Questions</h2>
        <Accordion type="single" collapsible className="mt-8">
          {FAQ.map(([q, a]) => (
            <AccordionItem key={q} value={q}>
              <AccordionTrigger className="text-base">{q}</AccordionTrigger>
              <AccordionContent className="text-muted-foreground">{a}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      <section className="mx-auto max-w-6xl px-4 pb-24 sm:px-6">
        <Card className="relative overflow-hidden border-0 bg-primary text-primary-foreground">
          <div className="bg-grid absolute inset-0 opacity-20" aria-hidden="true" />
          <CardContent className="relative flex flex-wrap items-center justify-between gap-6 py-6 md:px-10">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight md:text-3xl">Your first lesson takes ten minutes.</h2>
              <p className="mt-2 opacity-85">Set your goal, take a short check, and get a plan built for you.</p>
            </div>
            <Button asChild size="lg" variant="secondary" className="h-11 px-6 text-sm">
              <Link href="/login">Get started <ArrowRight data-icon="inline-end" /></Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <footer className="border-t">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-4 py-8 text-sm text-muted-foreground sm:px-6">
          <span>© {new Date().getFullYear()} Socrat</span>
          <span>Practice links open on LeetCode, CSES and Codeforces.</span>
        </div>
      </footer>
    </div>
  );
}
