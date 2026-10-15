'use client';

import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type HTMLAttributes, type ReactNode } from 'react';
import { prefersReducedMotion } from '@/lib/motion';
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
  return <div key={pathname} className={first.current ? undefined : 'animate-in fade-in slide-in-from-bottom-3 duration-300 ease-[var(--ease-soft)]'}>{children}</div>;
}

/**
 * A thin page-scroll bar at the very top of the window. Every app route renders it, so it uses
 * a passive scroll listener rather than motion's scroll and spring engine (about 40 KB gzip).
 */
export function ScrollBar() {
  const bar = useRef<HTMLDivElement>(null);
  useEffect(() => {
    let frame = 0;
    const update = () => {
      frame = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      if (bar.current) bar.current.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
    update();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, []);
  return <div ref={bar} aria-hidden="true" style={{ transform: 'scaleX(0)' }} className="pointer-events-none fixed inset-x-0 top-0 z-[60] h-0.5 origin-left bg-primary transition-transform duration-150 ease-out" />;
}
