'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ChevronDown, Menu, X } from 'lucide-react';
import { api } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Course } from '@/lib/types';
import { Illustration } from '@/components/socrat/illustration';
import { StatusIcon, StatusLabel } from '@/components/socrat/status';
import { Wordmark } from '@/components/socrat/wordmark';
import { ArrowCircle, Button } from '@/components/ui/button';
import { DrawLine, InView, Parallax, ScrollMeter, ScrubText, Underline } from '@/components/motion';
import { Reveal } from '@/components/common';
import { ThemeToggle } from '@/components/theme-toggle';

const PATHS = [
  { id: 'zero', name: 'Programming from Zero', title: 'Start from the beginning', description: 'Write your first programs in Python, C++ or Java and understand what each line does.', tone: 'grain bg-forest text-forest-foreground', pill: 'ink' as const },
  { id: 'interview', name: 'DSA for Interviews', title: 'Data structures and algorithms for interviews', description: 'Learn the patterns behind the questions and explain your choices and trade-offs.', tone: 'bg-foreground text-background', pill: 'ink' as const },
  { id: 'competitive', name: 'Competitive Programming', title: 'Competitive programming', description: 'Contest techniques, timed practice and upsolving, on a foundation of understanding.', tone: 'bg-cream text-cream-foreground', pill: 'solid' as const },
];

const FAQ = [
  ['Can I start without knowing how to code?', 'Yes. Programming from Zero starts with your first program. You choose Python, C++ or Java, and a short placement check finds the right starting point.'],
  ['How is this different from a problem list?', 'A problem list gives you options. Socrat connects lessons, checks and practice into a plan built from your goal, your time and what you have shown you can do.'],
  ['Will the tutor give me the answer?', 'The tutor starts with a question or a small hint. Help gets more specific as you make real attempts. A full walkthrough is available after you have worked through the problem.'],
  ['What counts as proof?', 'Reading a lesson does not. Concept checks, judged code and reviews do, and help you received lowers how much a success counts.'],
  ['Where do the practice problems come from?', 'Socrat has its own judged problems and a curated index of LeetCode, CSES and Codeforces problems. External statements and submissions stay on those platforms.'],
];

/** A minimal frame around a real component rendering with sample data. */
function Frame({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <figure className={`flex flex-col overflow-hidden rounded-card border bg-background ${className ?? ''}`}>
      <figcaption className="flex items-center justify-between gap-3 border-b px-5 py-3 text-[13px]">
        <span className="font-semibold">{title}</span>
        <span className="rounded-full border border-border-strong px-2.5 py-0.5 font-semibold text-muted-foreground">Sample data</span>
      </figcaption>
      <div className="flex-1 p-4 sm:p-5" aria-hidden="true">{children}</div>
    </figure>
  );
}

function TodaySample() {
  return (
    <div className="relative overflow-hidden rounded-[24px] bg-forest p-5 text-forest-foreground" data-tone="hero">
      <Illustration name="orbit" className="absolute -top-4 -right-6 size-28 opacity-90" />
      <p className="type-label">Next for you</p>
      <p className="mt-3 max-w-[11ch] font-display text-3xl leading-none font-bold tracking-[-0.035em]">Two-pointer problems</p>
      <p className="mt-2 text-sm">Next in your plan.</p>
      <div className="mt-4 flex gap-2">
        <span className="rounded-full border border-current px-3 py-1 text-[13px] font-semibold">practice</span>
        <span className="rounded-full border border-current px-3 py-1 text-[13px] font-semibold">45 min</span>
      </div>
      <span className="mt-5 inline-flex h-11 items-center gap-2 rounded-full bg-ink pr-2 pl-5 text-[15px] font-semibold text-ink-foreground">Open problem <ArrowCircle /></span>
    </div>
  );
}

function ProblemSample() {
  const rows: [boolean, string][] = [[true, 'Example 1'], [true, 'Example 2'], [true, 'Duplicates'], [false, 'Edge case: empty array']];
  return (
    <div className="grid gap-3">
      <pre className="code-block text-[13px]!"><code>
        <span style={{ color: 'var(--syntax-keyword)' }}>def</span> <span style={{ color: 'var(--syntax-function)' }}>find_pair</span>(numbers, target):{'\n'}
        {'    '}left, right = <span style={{ color: 'var(--syntax-number)' }}>0</span>, len(numbers) - <span style={{ color: 'var(--syntax-number)' }}>1</span>{'\n'}
        {'    '}<span style={{ color: 'var(--syntax-keyword)' }}>while</span> left &lt; right:{'\n'}
        {'        '}total = numbers[left] + numbers[right]{'\n'}
        {'        '}<span style={{ color: 'var(--syntax-comment)' }}># which pointer moves next?</span>
      </code></pre>
      <div className="rounded-[20px] border bg-card p-4">
        <p className="font-display text-lg font-bold tracking-[-0.02em]">3 of 4 tests passed</p>
        <ul className="mt-2 grid gap-1.5 text-sm">
          {rows.map(([ok, name]) => (
            <li key={name} className="flex items-center gap-2">
              {ok ? <span className="grid size-5 place-items-center rounded-full bg-cream text-cream-foreground"><svg viewBox="0 0 24 24" className="size-3" fill="none" stroke="currentColor" strokeWidth="3"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg></span> : <StatusIcon status="needs_practice" size={20} />}
              <span className={ok ? '' : 'font-semibold'}>{ok ? 'Passed' : name}</span>
              {ok ? <span className="text-muted-foreground">{name}</span> : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function PlaygroundSample() {
  const values = [1, 3, 5, 7, 9];
  return (
    <div className="overflow-hidden rounded-[20px] border bg-card">
      <div className="grid gap-4 p-5">
        <p className="text-sm text-muted-foreground">Find two numbers that add up to 8.</p>
        <div className="flex justify-center gap-2">
          {values.map((v, i) => (
            <span key={v} className={`grid size-11 place-items-center rounded-[12px] font-display text-lg font-bold ${i === 0 || i === 3 ? 'bg-primary text-primary-foreground' : 'bg-raised'}`}>{v}</span>
          ))}
        </div>
        <p className="text-center text-sm font-semibold">1 + 7 = 8. Found.</p>
      </div>
      <div className="flex items-center gap-2 border-t px-4 py-3 text-[13px] font-semibold">
        <span className="rounded-full border border-border-strong px-3 py-1.5">Previous</span>
        <span className="rounded-full bg-primary px-3 py-1.5 text-primary-foreground">Play</span>
        <span className="rounded-full border border-border-strong px-3 py-1.5">Next</span>
        <span className="ml-auto text-muted-foreground tabular-nums">Step 3 of 3</span>
      </div>
    </div>
  );
}

export default function Home() {
  const { profile, loading } = useSession();
  const router = useRouter();
  const [courses, setCourses] = useState<Course[]>([]);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? '/today');
  }, [loading, profile, router]);

  useEffect(() => {
    let active = true;
    api.get<{ items: Course[] }>('/courses').then(r => { if (active) setCourses(r.items); }).catch(() => undefined);
    return () => { active = false; };
  }, []);

  const links = [['#how', 'How it works'], ['#paths', 'Paths'], ['#faq', 'FAQ']] as const;

  return (
    <div className="min-h-dvh bg-background text-foreground">
      <header
        className="landing-nav fixed inset-x-0 top-3 z-50 px-3 sm:px-6"
        onKeyDown={event => { if (event.key === 'Escape' && menu) { setMenu(false); event.currentTarget.querySelector<HTMLButtonElement>('[data-menu-button]')?.focus(); } }}
      >
        <div className="glass-nav mx-auto flex h-14 max-w-[1100px] items-center justify-between gap-4 rounded-full border px-4 shadow-floating sm:px-5">
          <Link href="/" aria-label="Socrat home" className="rounded-full"><Wordmark /></Link>
          <nav aria-label="Site" className="hidden items-center gap-8 text-[15px] font-medium md:flex">
            {links.map(([href, label]) => <a key={href} href={href} className="text-muted-foreground transition-colors hover:text-foreground">{label}</a>)}
          </nav>
          <div className="flex items-center gap-2 sm:gap-4">
            <Link href="/login" className="hidden min-h-11 items-center text-[15px] font-semibold underline-offset-4 hover:underline sm:inline-flex">Log in</Link>
            <ThemeToggle />
            <Button asChild size="sm"><Link href="/login">Get started</Link></Button>
            <Button data-menu-button variant="ghost" size="icon" className="md:hidden" aria-label={menu ? 'Close navigation' : 'Open navigation'} aria-expanded={menu} aria-controls={menu ? 'landing-mobile-nav' : undefined} onClick={() => setMenu(!menu)}>
              {menu ? <X /> : <Menu />}
            </Button>
          </div>
        </div>
        {menu ? (
          <nav id="landing-mobile-nav" aria-label="Mobile site" className="mx-auto mt-2 grid max-w-[1100px] rounded-card border bg-background px-4 py-2 shadow-floating md:hidden">
            {links.map(([href, label]) => <a key={href} href={href} onClick={() => setMenu(false)} className="flex min-h-12 items-center text-[17px] font-semibold">{label}</a>)}
            <Link href="/login" className="flex min-h-12 items-center text-[17px] font-semibold">Log in</Link>
          </nav>
        ) : null}
      </header>

      <div>
        {/* Hero */}
        <section aria-labelledby="hero-title" className="mx-auto grid max-w-[1440px] items-center gap-10 px-4 pt-28 pb-16 sm:px-6 lg:grid-cols-[1.15fr_1fr] lg:gap-16 lg:px-10 lg:pt-36 lg:pb-24">
          <div>
            <Reveal><h1 id="hero-title" className="type-display-xl">Learn it.<br /><Underline>Then prove it.</Underline></h1></Reveal>
            <Reveal index={1}><p className="type-body-l mt-6 max-w-xl text-muted-foreground">A tutor that asks before it tells, a plan built around your goal, and checks that show what you can do on your own.</p></Reveal>
            <Reveal index={2}>
              <div className="mt-8 flex flex-wrap items-center gap-5">
                <Button asChild size="lg"><Link href="/login">Get started<ArrowCircle /></Link></Button>
                <Link href="/login" className="inline-flex min-h-11 items-center text-[17px] font-semibold underline underline-offset-4">Log in</Link>
              </div>
            </Reveal>
          </div>
          <Parallax className="mx-auto w-full max-w-xl"><Reveal index={2} className="grid w-full gap-3 rounded-card border bg-card p-4 text-card-foreground shadow-floating sm:p-6">
            <TodaySample />
            <div className="rounded-[20px] border bg-card p-4 text-card-foreground" aria-hidden="true">
              <p className="font-display text-lg font-bold tracking-[-0.02em]">3 of 4 tests passed</p>
              <p className="mt-1 text-sm text-muted-foreground">Edge case: empty array. Tutor hints are recorded.</p>
            </div>
            <ScrollMeter className="rounded-[20px] border bg-card p-4 text-card-foreground" />
          </Reveal></Parallax>
        </section>

        {/* How it works: introduces the status system. */}
        <section id="how" aria-labelledby="how-title" className="mx-auto max-w-[1440px] scroll-mt-20 px-4 py-16 sm:px-6 lg:px-10 lg:py-24">
          <h2 id="how-title" className="type-display-m max-w-2xl">Read. Check. Prove.</h2>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">Every skill shows the difference between reading about it, practising it with help and showing it in a check.</p>
          <ol className="mt-10 lg:mt-14">
            {([
              ['Read', 'read', 'Read', 'Lessons with worked traces, edge cases and self-checks. Reading alone never counts as mastery.'],
              ['Check', 'practised', 'Practised with help', 'Concept checks and judged problems. The tutor helps, and help is recorded.'],
              ['Prove', 'mastered', 'Mastered', 'Checkpoints and reviews confirm what holds up over time, as the questions get harder.'],
            ] as const).map(([title, status, label, text], i) => (
              <li key={title}>
                <DrawLine />
                <ScrubText className="scroll-row grid grid-cols-[2.5rem_minmax(0,1fr)] items-center gap-x-4 gap-y-3 py-7 md:grid-cols-[4rem_minmax(0,1.1fr)_minmax(0,1.3fr)_auto] lg:py-10">
                  <span className="font-mono text-sm text-muted-foreground">0{i + 1}</span>
                  <h3 className="type-display-l">{title}</h3>
                  <p className="col-start-2 text-base text-muted-foreground md:col-start-auto">{text}</p>
                  <div className="col-start-2 flex items-center gap-3 md:col-start-auto">
                    <StatusIcon status={status} size={28} />
                    <StatusLabel status={status} detail={label} muted className="text-[13px]" />
                  </div>
                </ScrubText>
              </li>
            ))}
            <li><DrawLine /></li>
          </ol>
        </section>

        {/* Product proof: real components with sample data. */}
        <section aria-labelledby="inside-title" className="mx-auto max-w-[1440px] px-4 py-16 sm:px-6 lg:px-10 lg:py-24">
          <h2 id="inside-title" className="type-display-m max-w-2xl">Inside Socrat</h2>
          <p className="mt-3 max-w-2xl text-base text-muted-foreground">One next step each day, a real editor with judged tests, and visuals you can explore.</p>
          <div className="mt-8 grid gap-4 lg:grid-cols-3 lg:gap-6">
            <InView index={0} className="flex"><Frame title="Today" className="w-full"><TodaySample /></Frame></InView>
            <InView index={1} className="flex"><Frame title="Problem workspace" className="w-full"><ProblemSample /></Frame></InView>
            <InView index={2} className="flex"><Frame title="Playground" className="w-full"><PlaygroundSample /></Frame></InView>
          </div>
        </section>

        {/* Learning paths */}
        <section id="paths" aria-labelledby="paths-title" className="mx-auto max-w-[1440px] scroll-mt-20 px-4 py-16 sm:px-6 lg:px-10 lg:py-24">
          <h2 id="paths-title" className="type-display-m">Three ways in</h2>
          <div className="mt-8 grid gap-3 md:grid-cols-3 md:gap-4 lg:gap-6">
            {PATHS.map((path, i) => {
              const course = courses.find(c => c.id === path.id || c.title === path.name);
              return (
                <InView key={path.id} index={i} className={`flex min-h-80 flex-col gap-4 rounded-card p-6 lg:p-8 ${path.tone}`}>
                  <p className="type-label">{course?.title ?? path.name}</p>
                  <h3 className="font-display text-3xl leading-[1.05] font-bold tracking-[-0.035em]">{path.title}</h3>
                  <p className="text-base">{path.description}</p>
                  {course ? <p className="path-count text-[13px] font-semibold">{course.concept_count} skills, {course.problem_count} judged problems</p> : null}
                  <div className="mt-auto">
                    <Button asChild variant={path.pill}><Link href="/login" aria-label={`Get started with ${path.name}`}>Get started<ArrowCircle /></Link></Button>
                  </div>
                </InView>
              );
            })}
          </div>
        </section>

        {/* FAQ */}
        <section id="faq" aria-labelledby="faq-title" className="mx-auto grid max-w-[1440px] scroll-mt-20 gap-8 px-4 py-16 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:px-10 lg:py-24">
          <h2 id="faq-title" className="type-display-m">Questions</h2>
          <div className="grid gap-3">
            {FAQ.map(([question, answer]) => (
              <details key={question} className="landing-question group rounded-[20px] border bg-card">
                <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-[17px] font-semibold [&::-webkit-details-marker]:hidden">
                  {question}
                  <ChevronDown className="size-5 flex-none transition-transform group-open:rotate-180" aria-hidden="true" />
                </summary>
                <p className="px-5 pb-5 text-[15px] text-muted-foreground">{answer}</p>
              </details>
            ))}
          </div>
        </section>

        {/* Final call to action */}
        <section aria-labelledby="cta-title" className="mx-auto max-w-[1440px] px-4 pb-16 sm:px-6 lg:px-10 lg:pb-24">
          <InView data-tone="hero" className="flex flex-col items-start gap-6 rounded-card bg-forest p-8 text-forest-foreground lg:flex-row lg:items-end lg:justify-between lg:p-12">
            <ScrubText from={0.35}><h2 id="cta-title" className="type-display-l max-w-[14ch]">Start where you are.</h2></ScrubText>
            <Button asChild variant="ink" size="lg"><Link href="/login">Get started<ArrowCircle /></Link></Button>
          </InView>
        </section>
      </div>

      <footer className="border-t">
        <div className="mx-auto flex max-w-[1440px] flex-wrap items-center justify-between gap-4 px-4 py-8 sm:px-6 lg:px-10">
          <Wordmark size={24} />
          <nav aria-label="Footer" className="flex flex-wrap gap-6 text-[15px] text-muted-foreground">
            <a href="#how" className="hover:text-foreground">How it works</a>
            <a href="#paths" className="hover:text-foreground">Paths</a>
            <a href="#faq" className="hover:text-foreground">FAQ</a>
            <Link href="/login" className="hover:text-foreground">Log in</Link>
          </nav>
          <p className="text-[13px] text-muted-foreground">© {new Date().getFullYear()} Socrat</p>
        </div>
      </footer>
    </div>
  );
}
