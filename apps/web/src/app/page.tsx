'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowDown, ArrowRight, ArrowUpRight, Check, ChevronRight, Code2, Menu, Plus, X } from 'lucide-react';
import { api } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Course, Language } from '@/lib/types';
import { LANGUAGE_LABEL } from '@/lib/routes';
import { RibbonScene } from '@/components/landing/ribbon-scene';
import './landing.css';

const PATHS = [
  { id: 'zero', title: 'Your first line of code.', name: 'Programming from Zero', audience: 'For the curious beginner', description: 'Start with the fundamentals. Build small programs, understand what each line does, and find your feet in Python, C++ or Java.', topics: ['Programming basics', 'Loops & functions', 'Your first problems'] },
  { id: 'interview', title: 'Think past the interview.', name: 'DSA for Interviews', audience: 'For the next career move', description: 'Understand the patterns behind the questions. Learn to explain your choices, reason about trade-offs, and solve unfamiliar problems.', topics: ['Data structures', 'Problem patterns', 'Complexity & trade-offs'] },
  { id: 'competitive', title: 'Your contest edge.', name: 'Competitive Programming', audience: 'For the problem solver', description: 'Build speed on a foundation of understanding. Practice contest techniques, timed problems, and the upsolving that makes the next attempt better.', topics: ['Contest techniques', 'Timed practice', 'Upsolving & review'] },
];

const FAQ = [
  ['Can I start without knowing how to code?', 'Yes. Programming from Zero starts with your first program. You choose Python, C++ or Java, and a short placement check helps Socrat find the right starting point.'],
  ['What makes Socrat different from a problem list?', 'A problem list gives you options. Socrat connects concepts, lessons and practice into a plan based on your goal, available time and demonstrated understanding.'],
  ['Will the tutor give me the answer?', 'The tutor starts with a question or a small hint. Help gets more specific as you make real attempts, with a walkthrough available after you have worked through the problem.'],
  ['What happens if I miss a day?', 'Your plan adjusts to your schedule. Reviews bring back concepts that need another look, and you can continue without squeezing missed work into one session.'],
  ['Where do the practice problems come from?', 'Socrat includes its own judged problems and a curated practice index linking to LeetCode, CSES and Codeforces. External problem statements and submissions stay on those platforms.'],
];

const CODE: Record<Language, string[]> = {
  python: ['def find_pair(numbers, target):', '    left, right = 0, len(numbers) - 1', '', '    while left < right:', '        total = numbers[left] + numbers[right]', '        if total == target:', '            return left, right', '        # Which pointer should move next?'],
  cpp: ['pair<int, int> findPair(vector<int>& a, int target) {', '    int left = 0, right = int(a.size()) - 1;', '', '    while (left < right) {', '        int total = a[left] + a[right];', '        if (total == target) return {left, right};', '        // Which pointer should move next?', '    }', '    return {-1, -1};', '}'],
  java: ['int[] findPair(int[] a, int target) {', '    int left = 0, right = a.length - 1;', '', '    while (left < right) {', '        int total = a[left] + a[right];', '        if (total == target) return new int[]{left, right};', '        // Which pointer should move next?', '    }', '    return new int[]{-1, -1};', '}'],
};

function Mark() {
  return <span className="socrat-mark" aria-hidden="true"><span /><span /><span /></span>;
}

export default function Home() {
  const { profile, loading } = useSession();
  const router = useRouter();
  const root = useRef<HTMLDivElement>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [language, setLanguage] = useState<Language>('python');
  const [hint, setHint] = useState(false);
  const [menu, setMenu] = useState(false);

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? '/today');
  }, [loading, profile, router]);

  useEffect(() => {
    let active = true;
    api.get<{ items: Course[] }>('/courses').then(r => { if (active) setCourses(r.items); }).catch(() => undefined);
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let disposed = false;
    let cleanup: (() => void) | undefined;
    Promise.all([import('gsap'), import('gsap/ScrollTrigger')]).then(([{ gsap }, { ScrollTrigger }]) => {
      if (disposed || !root.current) return;
      gsap.registerPlugin(ScrollTrigger);
      const media = gsap.matchMedia();
      media.add('(prefers-reduced-motion: no-preference)', () => {
        gsap.from('.landing-nav', { y: -14, duration: 0.7, ease: 'power3.out' });
        gsap.from('[data-hero-enter]', { y: 26, duration: 1, stagger: 0.09, ease: 'power3.out' });
        gsap.to('.ribbon-stage', { scale: 1.55, y: 140, rotationX: 8, transformPerspective: 900, ease: 'none', scrollTrigger: { trigger: '.landing-opening', start: 'top top', end: 'bottom top', scrub: 0.8 } });
        gsap.to('.map-center', { y: -24, scale: 1.08, ease: 'none', scrollTrigger: { trigger: '.learning-map', start: 'top bottom', end: 'bottom top', scrub: 1 } });
        gsap.to('.map-orbit', { rotation: '+=35', ease: 'none', scrollTrigger: { trigger: '.learning-map', start: 'top bottom', end: 'bottom top', scrub: 1 } });
        root.current?.querySelectorAll<HTMLElement>('.path-sculpture').forEach(sculpture => {
          gsap.to(sculpture.children, { y: index => (index - 2) * 7, z: index => index * 8, ease: 'none', scrollTrigger: { trigger: sculpture.closest('.path-row'), start: 'top bottom', end: 'bottom top', scrub: 0.8 } });
        });
        gsap.to('.cta-ribbons span', { y: index => `-=${60 + index * 45}`, ease: 'none', scrollTrigger: { trigger: '.landing-cta', start: 'top bottom', end: 'bottom top', scrub: 1 } });
        root.current?.querySelectorAll<HTMLElement>('[data-reveal]').forEach((section, index) => {
          gsap.from(section, { y: index % 2 ? 20 : 32, duration: 0.85, ease: 'power3.out', scrollTrigger: { trigger: section, start: 'top 92%', once: true } });
        });
      }, root);
      cleanup = () => media.revert();
    }).catch(() => undefined);
    return () => { disposed = true; cleanup?.(); };
  }, []);

  return (
    <div ref={root} className="socrat-landing" data-theme="socrat-landing">
      <div className="landing-opening">
        <header className="landing-nav landing-width" onKeyDown={event => { if (event.key === 'Escape' && menu) { setMenu(false); event.currentTarget.querySelector<HTMLButtonElement>('.landing-menu')?.focus(); } }}>
          <Link href="/" className="landing-brand" aria-label="Socrat home"><Mark />socrat<span className="brand-period">.</span></Link>
          <nav aria-label="Site" className="landing-desktop-links">
            <a href="#how">Approach</a><a href="#experience">Experience</a><a href="#courses">Paths</a>
          </nav>
          <div className="landing-nav-actions">
            <Link href="/login" className="landing-signin">Sign in <ArrowUpRight size={16} aria-hidden="true" /></Link>
            <Link href="/login" className="landing-btn landing-btn-dark daisy-btn">Get started <ArrowUpRight size={16} aria-hidden="true" /></Link>
            <button className="landing-menu daisy-btn daisy-btn-ghost" aria-label={menu ? 'Close navigation' : 'Open navigation'} aria-expanded={menu} aria-controls={menu ? 'landing-mobile-nav' : undefined} onClick={() => setMenu(!menu)}>{menu ? <X /> : <Menu />}</button>
          </div>
          {menu ? <nav id="landing-mobile-nav" className="landing-mobile-links" aria-label="Mobile site">
            <a href="#how" onClick={() => setMenu(false)}>The approach <ArrowRight size={18} /></a>
            <a href="#experience" onClick={() => setMenu(false)}>Inside Socrat <ArrowRight size={18} /></a>
            <a href="#courses" onClick={() => setMenu(false)}>Learning paths <ArrowRight size={18} /></a>
            <Link href="/login">Sign in <ArrowUpRight size={18} /></Link>
          </nav> : null}
        </header>

        <section className="landing-hero" aria-labelledby="hero-title">
          <RibbonScene />
          <div className="hero-copy landing-width">
            <p className="landing-eyebrow" data-hero-enter><span className="live-dot" /> A better way to learn programming</p>
            <h1 id="hero-title" data-hero-enter>Think deeper.<br />Code better.</h1>
            <p className="hero-description" data-hero-enter>A plan that meets you where you are. A tutor that asks the right questions.<br className="desktop-break" /> Build the understanding to solve what comes next.</p>
            <div className="hero-actions" data-hero-enter>
              <Link href="/login" className="landing-btn landing-btn-lime daisy-btn">Start learning <ArrowUpRight size={19} aria-hidden="true" /></Link>
              <a href="#experience" className="landing-btn landing-btn-outline daisy-btn">Explore the experience <ArrowDown size={17} aria-hidden="true" /></a>
            </div>
            <p className="hero-note" data-hero-enter>From your first program to your next interview.</p>
          </div>
          <div className="hero-baseline landing-width"><span>Less memorizing. More understanding.</span><a href="#how" aria-label="Discover the Socrat approach"><ArrowDown size={18} aria-hidden="true" /></a><span>Python / C++ / Java</span></div>
        </section>
      </div>

      <section id="how" className="landing-approach landing-section" aria-labelledby="approach-title">
        <div className="landing-width">
          <div className="section-heading" data-reveal>
            <p className="landing-eyebrow">Built around the way you learn</p>
            <h2 id="approach-title">A little direction.<br />A lot of possibility.</h2>
            <p>You bring the curiosity. Socrat turns it into a clear next step, with lessons, practice and questions that move you forward.</p>
          </div>
          <div className="approach-layout">
            <div className="learning-map" data-reveal aria-label="Learning journey: your starting point, a personal plan, guided practice and independent understanding">
              <div className="map-orbit orbit-outer" /><div className="map-orbit orbit-inner" />
              <div className="map-center"><Mark /><span>Your next<br />breakthrough</span></div>
              <span className="map-node node-start"><span /><span>Your starting point</span></span>
              <span className="map-node node-plan"><span /><span>Your own plan</span></span>
              <span className="map-node node-practice"><span /><span>Guided practice</span></span>
              <span className="map-node node-understand"><Check size={17} aria-hidden="true" /><span>Real understanding</span></span>
              <span className="map-caption">Progress has a path. Yours.</span>
            </div>
            <div className="approach-steps">
              <article data-reveal><span className="step-symbol"><Code2 size={22} aria-hidden="true" /></span><div><h3>Start where you are.</h3><p>A short adaptive check finds what you know, so you spend time on what you need.</p></div></article>
              <article data-reveal><span className="step-symbol"><ArrowRight size={22} aria-hidden="true" /></span><div><h3>Know what comes next.</h3><p>A daily plan connects the right concepts and problems to your goal and the time you have.</p></div></article>
              <article data-reveal><span className="step-symbol question-symbol">?</span><div><h3>Find your own answer.</h3><p>Hints help you reason through the problem. Reviews help the understanding stay with you.</p></div></article>
            </div>
          </div>
        </div>
      </section>

      <section id="experience" className="landing-experience landing-section" aria-labelledby="experience-title">
        <div className="landing-width">
          <div className="experience-heading" data-reveal><div><p className="landing-eyebrow">Small steps. Real understanding.</p><h2 id="experience-title">Meet your thinking space.</h2></div><p>Read the idea. Try it in code. Ask a better question.<br />Everything you need to get from “I’m stuck” to “I get it.”</p></div>
          <div className="experience-workspace" data-ui data-reveal>
            <aside className="workspace-lesson">
              <div className="workspace-wordmark"><Mark />socrat<span> / Example session</span></div>
              <p className="workspace-label">The idea</p><h3>Two pointers.<br />One insight.</h3>
              <p>The numbers are sorted. Instead of checking every pair, start at opposite ends.</p>
              <div className="number-line" aria-label="Sorted numbers 1, 3, 5, 7, 9"><span className="pointer">1</span><span>3</span><span>5</span><span>7</span><span className="pointer">9</span></div>
              <div className="pointer-labels"><span>left</span><span>right</span></div>
              <p className="lesson-question">Looking for a total of 8.<br />The first pair gives you 10.<br /><strong>What would you change?</strong></p>
              <div className="lesson-next"><span>Concept → Practice → Review</span><ArrowRight size={17} aria-hidden="true" /></div>
            </aside>
            <div className="workspace-code">
              <div className="code-toolbar"><span>Practice / Find a pair</span><div className="language-options" role="group" aria-label="Example code language">{(['python', 'cpp', 'java'] as const).map(l => <button key={l} type="button" aria-pressed={language === l} onClick={() => setLanguage(l)}>{LANGUAGE_LABEL[l]}</button>)}</div></div>
              <pre tabIndex={0} aria-label={`${LANGUAGE_LABEL[language]} incomplete example for you to reason about`}><code>{CODE[language].map((line, i) => <span className={line.trim().startsWith('#') || line.trim().startsWith('//') ? 'code-line code-comment' : 'code-line'} key={`${language}-${i}`}><span className="line-number" aria-hidden="true">{i + 1}</span>{line || ' '}</span>)}</code></pre>
              <div className="code-example-note"><span className="live-dot" /> An unfinished example. The next step is yours.</div>
              <div className="workspace-tutor"><div className="tutor-heading"><span className="tutor-symbol">?</span><span>Your Socratic tutor</span><span>Guidance, one step at a time</span></div><p>“The total is too large. Since the numbers are sorted, which pointer could you move to make it smaller?”</p><button className="daisy-btn daisy-btn-ghost tutor-hint" aria-expanded={hint} aria-controls="example-hint" onClick={() => setHint(!hint)}>{hint ? 'Hide the hint' : 'Show me a hint'} {hint ? <X size={16} /> : <Plus size={16} />}</button><div id="example-hint" hidden={!hint} className="hint-answer">Try moving the right pointer one place to the left. You replace 9 with 7, and the new total is 1 + 7 = 8.</div></div>
            </div>
          </div>
          <div className="experience-footnote"><span>Learn in Python, C++ or Java.</span><span>Practice with a real editor, guided hints and concept checks.</span></div>
        </div>
      </section>

      <section id="courses" className="landing-paths landing-section" aria-labelledby="paths-title">
        <div className="landing-width">
          <div className="paths-heading" data-reveal><div><p className="landing-eyebrow">Different goals. The same curiosity.</p><h2 id="paths-title">Find your way in.</h2></div><p>Begin from zero, prepare for interviews, or train for contests.<br />Your starting point is just that: a start.</p></div>
          <div className="path-list">{PATHS.map((path, index) => {
            const course = courses.find(c => c.id === path.id || c.title === path.name);
            return <article className={`path-row path-${index}`} key={path.id} data-reveal><div className="path-art" aria-hidden="true"><div className="path-sculpture"><span /><span /><span /><span /><span /></div></div><div className="path-title"><p>{path.audience}</p><h3>{path.title}</h3><span>{course?.title ?? path.name}</span></div><div className="path-details"><p>{path.description}</p><div className="path-topics">{path.topics.map(t => <span key={t}>{t}</span>)}</div>{course ? <p className="path-count">{course.concept_count} concepts · {course.problem_count} judged problems</p> : null}</div><Link href="/login" className="path-link" aria-label={`Get started with ${path.name}`}><ArrowUpRight size={25} aria-hidden="true" /></Link></article>;
          })}</div>
          <div className="practice-sources" data-reveal><p>More room to practice.<br /><span>A curated index of problems from</span></p><div><span>LeetCode</span><span>CSES</span><span>Codeforces</span></div><a href="#experience">A concept before a problem <ChevronRight size={16} aria-hidden="true" /></a></div>
        </div>
      </section>

      <section className="landing-faq landing-section" aria-labelledby="faq-title">
        <div className="landing-width faq-layout"><div data-reveal><p className="landing-eyebrow">Good questions are a start.</p><h2 id="faq-title">A little more clarity.</h2><p>Curious about how it all works?<br />Start here.</p></div><div className="faq-list" data-reveal>{FAQ.map(([question, answer]) => <details className="daisy-collapse daisy-collapse-plus landing-question" key={question}><summary className="daisy-collapse-title">{question}</summary><div className="daisy-collapse-content"><p>{answer}</p></div></details>)}</div></div>
      </section>

      <section className="landing-cta" aria-labelledby="cta-title"><div className="landing-width" data-reveal><p className="landing-eyebrow">Your next chapter starts with a question.</p><h2 id="cta-title">What will you<br />solve next?</h2><div><p>Set your goal. Find your starting point.<br />Take the next step with Socrat.</p><Link href="/login" className="landing-btn landing-btn-lime daisy-btn">Let’s find out <ArrowUpRight size={21} aria-hidden="true" /></Link></div></div><div className="cta-ribbons" aria-hidden="true"><span /><span /><span /><span /></div></section>
      <footer className="landing-footer"><div className="landing-width"><div className="footer-top"><Link href="/" className="landing-brand" aria-label="Socrat home"><Mark />socrat.</Link><p>Learn to think.<br />Then let your code do the talking.</p><nav aria-label="Footer"><a href="#how">The approach</a><a href="#courses">Learning paths</a><a href="#faq-title">Questions</a></nav></div><div className="footer-bottom"><span>© {new Date().getFullYear()} Socrat</span><span>Made for the curious.</span><a href="#hero-title">Back to top ↑</a></div></div></footer>
    </div>
  );
}
