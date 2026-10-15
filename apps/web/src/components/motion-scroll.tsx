'use client';

// Scroll-driven effects for the landing page. They use passive scroll listeners, an
// IntersectionObserver and CSS transitions rather than motion's scroll engine, which alone put
// the landing page over the 250 KB first-load budget.
import { useEffect, useRef, useState, type ReactNode, type RefObject } from 'react';
import { prefersReducedMotion } from '@/lib/motion';
import { cn } from '@/lib/utils';

/** Calls `update` once per frame while the page scrolls or resizes, and once on mount. */
function useScrollFrame(update: () => void) {
  const latest = useRef(update);
  latest.current = update;
  useEffect(() => {
    if (prefersReducedMotion()) return;
    let frame = 0;
    const run = () => { frame = 0; latest.current(); };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(run); };
    run();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, []);
}

/** True once the element has entered the viewport (immediately when motion is reduced). */
function useSeen(ref: RefObject<Element | null>, margin = '0px 0px -8% 0px') {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const node = ref.current;
    if (!node || prefersReducedMotion() || typeof IntersectionObserver === 'undefined') { setSeen(true); return; }
    const io = new IntersectionObserver(entries => {
      if (entries.some(e => e.isIntersecting)) { setSeen(true); io.disconnect(); }
    }, { rootMargin: margin });
    io.observe(node);
    return () => io.disconnect();
  }, [ref, margin]);
  return seen;
}

const clamp = (value: number) => Math.min(1, Math.max(0, value));

/** Display text that settles into place as it scrolls into the reading zone. */
export function ScrubText({ children, className, rise = 8 }: { children: ReactNode; className?: string; rise?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useScrollFrame(() => {
    const node = ref.current;
    if (!node) return;
    // 0 when the top reaches 95% of the viewport height, 1 at 55%.
    const top = node.getBoundingClientRect().top / window.innerHeight;
    // A rise, not a fade: text below the fold stays at full contrast (WCAG 1.4.3).
    node.style.transform = `translateY(${(rise * (1 - clamp((0.95 - top) / 0.4))).toFixed(2)}px)`;
  });
  return <div ref={ref} className={className}>{children}</div>;
}

/** A hairline that draws left to right when it enters the viewport. */
export function DrawLine({ className }: { className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const seen = useSeen(ref);
  return (
    <span
      ref={ref}
      aria-hidden="true"
      className={cn('block h-px origin-left bg-border-strong transition-transform duration-[900ms] ease-[var(--ease-soft)]', seen ? 'scale-x-100' : 'scale-x-0', className)}
    />
  );
}

/** A hand-drawn underline that strokes itself in under a word. */
export function Underline({ children, className }: { children: ReactNode; className?: string }) {
  const ref = useRef<SVGSVGElement>(null);
  const seen = useSeen(ref, '0px');
  return (
    <span className="relative inline-block">
      {children}
      <svg ref={ref} viewBox="0 0 300 14" preserveAspectRatio="none" className={cn('pointer-events-none absolute -bottom-[0.1em] left-0 h-[0.2em] w-full overflow-visible text-violet dark:text-proof', className)} aria-hidden="true">
        <path
          d="M3 8 C 45 2, 85 12, 128 7 S 205 3, 245 8 S 288 10, 297 5"
          fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" vectorEffect="non-scaling-stroke"
          pathLength={1} strokeDasharray="1" strokeDashoffset={seen ? 0 : 1}
          className="transition-[stroke-dashoffset] delay-[450ms] duration-[900ms] ease-[var(--ease-soft)]"
        />
      </svg>
    </span>
  );
}

/** Slides its children up slowly as the page scrolls (a light parallax). */
export function Parallax({ children, className, distance = 56 }: { children: ReactNode; className?: string; distance?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  useScrollFrame(() => {
    if (ref.current) ref.current.style.transform = `translateY(${(-distance * clamp(window.scrollY / 900)).toFixed(2)}px)`;
  });
  return <div ref={ref} className={className}>{children}</div>;
}

/** "You've learned n%": a meter that follows how far down the page you are. */
export function ScrollMeter({ className, label = "You've learned" }: { className?: string; label?: string }) {
  const text = useRef<HTMLSpanElement>(null);
  const bar = useRef<HTMLDivElement>(null);
  useScrollFrame(() => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const progress = max > 0 ? clamp(window.scrollY / max) : 0;
    if (text.current) text.current.textContent = `${Math.round(progress * 100)}%`;
    if (bar.current) bar.current.style.transform = `scaleX(${progress})`;
  });
  return (
    <div className={className}>
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span ref={text} className="font-display text-2xl font-bold tabular-nums">0%</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-raised">
        <div ref={bar} className="h-full origin-left rounded-full bg-primary transition-transform duration-200 ease-out" style={{ transform: 'scaleX(0)' }} />
      </div>
    </div>
  );
}
