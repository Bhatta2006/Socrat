'use client';

import { m, useScroll, useTransform, useSpring } from 'motion/react';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type HTMLAttributes, type ReactNode } from 'react';
import { prefersReducedMotion, useReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';

export const EASE = [0.2, 0.8, 0.2, 1] as const;

/**
 * Fades up once when scrolled into view, for content below the fold (above it, use Reveal).
 * Content is visible until the client mounts; only blocks still below the viewport are
 * hidden and then revealed, so a failed script or capture never leaves a blank section.
 */
export function InView({ children, index = 0, className, ...rest }: { children: ReactNode; index?: number; className?: string } & Omit<HTMLAttributes<HTMLDivElement>, 'children' | 'className'>) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<'shown' | 'waiting' | 'revealed'>('shown');
  useEffect(() => {
    const node = ref.current;
    if (!node || prefersReducedMotion() || typeof IntersectionObserver === 'undefined') return;
    if (node.getBoundingClientRect().top < window.innerHeight * 0.95) return;
    setState('waiting');
    const io = new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { setState('revealed'); io.disconnect(); }
    }, { rootMargin: '0px 0px -8% 0px' });
    io.observe(node);
    return () => io.disconnect();
  }, []);
  return (
    <div
      ref={ref}
      className={cn(className, state === 'waiting' && 'translate-y-5 opacity-0', state === 'revealed' && 'transition-[opacity,translate] duration-500 ease-[var(--ease-soft)]')}
      style={state === 'revealed' ? { transitionDelay: `${Math.min(index, 6) * 70}ms` } : undefined}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Route content: a short fade and rise on navigation (not on first load, so LCP is untouched). */
export function PageTransition({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const first = useRef(true);
  useEffect(() => { first.current = false; }, []);
  return (
    <m.div key={pathname} initial={first.current ? false : { opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, ease: EASE }}>
      {children}
    </m.div>
  );
}

/** Display text that wakes up as it scrolls into the reading zone (faint to full). */
export function ScrubText({ children, className, from = 0.2 }: { children: ReactNode; className?: string; from?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const { reduced } = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 0.95', 'start 0.55'] });
  const opacity = useTransform(scrollYProgress, [0, 1], [from, 1]);
  return <m.div ref={ref} style={reduced ? undefined : { opacity }} className={className}>{children}</m.div>;
}

/** A hairline that draws left to right when it enters the viewport. */
export function DrawLine({ className }: { className?: string }) {
  return (
    <m.span
      aria-hidden="true"
      className={cn('block h-px origin-left bg-border-strong', className)}
      initial={{ scaleX: 0 }}
      whileInView={{ scaleX: 1 }}
      viewport={{ once: true, margin: '0px 0px -8% 0px' }}
      transition={{ duration: 0.9, ease: EASE }}
    />
  );
}

/** A hand-drawn underline that strokes itself in under a word. */
export function Underline({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <span className="relative inline-block">
      {children}
      <svg viewBox="0 0 300 14" preserveAspectRatio="none" className={cn('pointer-events-none absolute -bottom-[0.1em] left-0 h-[0.2em] w-full overflow-visible text-violet dark:text-proof', className)} aria-hidden="true">
        <m.path
          d="M3 8 C 45 2, 85 12, 128 7 S 205 3, 245 8 S 288 10, 297 5"
          fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" vectorEffect="non-scaling-stroke"
          initial={{ pathLength: 0 }} whileInView={{ pathLength: 1 }} viewport={{ once: true }} transition={{ duration: 0.9, delay: 0.45, ease: EASE }}
        />
      </svg>
    </span>
  );
}

/** Slides its children up slowly as the page scrolls (a light parallax). */
export function Parallax({ children, className, distance = 56 }: { children: ReactNode; className?: string; distance?: number }) {
  const { reduced } = useReducedMotion();
  const { scrollY } = useScroll();
  const y = useTransform(scrollY, [0, 900], [0, -distance]);
  return <m.div style={reduced ? undefined : { y }} className={className}>{children}</m.div>;
}

/** "You've learned n%": a meter that follows how far down the page you are. */
export function ScrollMeter({ className, label = "You've learned" }: { className?: string; label?: string }) {
  const { scrollYProgress } = useScroll();
  const smooth = useSpring(scrollYProgress, { stiffness: 140, damping: 26, mass: 0.4 });
  const text = useTransform(smooth, v => `${Math.round(Math.min(1, Math.max(0, v)) * 100)}%`);
  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-muted-foreground">{label}</span>
        <m.span className="font-display text-2xl font-bold tabular-nums">{text}</m.span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-raised">
        <m.div className="h-full origin-left rounded-full bg-primary" style={{ scaleX: smooth }} />
      </div>
    </div>
  );
}

/** A thin page-scroll bar at the very top of the window. */
export function ScrollBar() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, { stiffness: 160, damping: 28, mass: 0.3 });
  return <m.div aria-hidden="true" style={{ scaleX }} className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-0.5 origin-left bg-primary" />;
}
