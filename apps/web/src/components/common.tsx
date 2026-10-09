'use client';

import Link from 'next/link';
import { animate, motion, useInView, useMotionValue, useTransform } from 'motion/react';
import { useEffect, useRef, type ReactNode } from 'react';
import { AlertCircle, ArrowLeft, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { BAND_LABEL } from '@/lib/routes';
import type { Band } from '@/lib/types';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

export function Page({ children, wide = false, narrow = false, className }: { children: ReactNode; wide?: boolean; narrow?: boolean; className?: string }) {
  return (
    <div className={cn('mx-auto w-full px-4 pt-6 pb-28 sm:px-6 md:pt-8 md:pb-16', wide ? 'max-w-[1440px]' : narrow ? 'max-w-3xl' : 'max-w-6xl', className)}>
      {children}
    </div>
  );
}

export function PageHeader({ eyebrow, title, description, actions, className }: { eyebrow?: ReactNode; title: ReactNode; description?: ReactNode; actions?: ReactNode; className?: string }) {
  return (
    <header className={cn('mb-8 flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="min-w-0 max-w-3xl">
        {eyebrow ? <p className="mb-2 text-xs font-medium tracking-wide text-primary uppercase">{eyebrow}</p> : null}
        <h1 className="text-3xl font-semibold tracking-tight text-balance md:text-4xl">{title}</h1>
        {description ? <p className="mt-2 text-base text-muted-foreground text-pretty">{description}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** Content-shaped placeholder; perceived as faster than a spinner. */
export function Loading({ label = 'Loading…', variant = 'page' }: { label?: string; variant?: 'page' | 'inline' }) {
  if (variant === 'inline') {
    return (
      <div className="grid gap-2 p-4" role="status" aria-label={label}>
        {[0, 1, 2, 3].map(i => <Skeleton key={i} className="h-9 w-full" />)}
      </div>
    );
  }
  return (
    <Page>
      <div role="status" aria-label={label} className="grid gap-6">
        <span className="sr-only">{label}</span>
        <div className="grid gap-3">
          <Skeleton className="h-3 w-28" />
          <Skeleton className="h-9 w-80 max-w-full" />
          <Skeleton className="h-4 w-[28rem] max-w-full" />
        </div>
        <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="grid gap-4">
            <Skeleton className="h-44 w-full rounded-xl" />
            <Skeleton className="h-64 w-full rounded-xl" />
          </div>
          <div className="grid content-start gap-4">
            <Skeleton className="h-40 w-full rounded-xl" />
            <Skeleton className="h-28 w-full rounded-xl" />
          </div>
        </div>
      </div>
    </Page>
  );
}

export function ErrorNote({ message, retry, className }: { message: string; retry?: () => void; className?: string }) {
  return (
    <Alert variant="destructive" className={cn('my-4', className)} role="alert">
      <AlertCircle />
      <AlertTitle>Something went wrong</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
        <span>{message}</span>
        {retry ? (
          <Button size="sm" variant="outline" onClick={retry}>
            <RotateCw data-icon="inline-start" /> Try again
          </Button>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}

/** Animated SVG ring for goal-gradient progress (daily minutes, scores, course progress). */
export function Ring({ value, label, size = 64, stroke = 6, className, tone = 'primary' }: { value: number; label: ReactNode; size?: number; stroke?: number; className?: string; tone?: 'primary' | 'streak' | 'success' }) {
  const clamped = Math.max(0, Math.min(100, value));
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const color = tone === 'streak' ? 'var(--streak)' : tone === 'success' ? 'var(--success)' : 'var(--primary)';
  return (
    <div className={cn('relative grid flex-none place-items-center', className)} style={{ width: size, height: size }} role="img" aria-label={`${Math.round(clamped)} percent`}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--muted)" strokeWidth={stroke} />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference * (1 - clamped / 100) }}
          transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
        />
      </svg>
      <span className="absolute inset-0 grid place-items-center text-sm font-semibold tabular-nums">{label}</span>
    </div>
  );
}

/** Counts up to a number once it scrolls into view. */
export function NumberTicker({ value, className }: { value: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const count = useMotionValue(0);
  const rounded = useTransform(count, v => Math.round(v).toLocaleString());
  useEffect(() => {
    if (!inView) return;
    const controls = animate(count, value, { duration: 0.8, ease: 'easeOut' });
    return () => controls.stop();
  }, [count, inView, value]);
  return <motion.span ref={ref} className={cn('tabular-nums', className)}>{rounded}</motion.span>;
}

export function BandBadge({ band, className }: { band: Band; className?: string }) {
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground', className)}>
      <span className={`band-dot band-${band}`} aria-hidden="true" />
      {BAND_LABEL[band]}
    </span>
  );
}

export function BackLink({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link href={href} className="mb-5 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground">
      <ArrowLeft className="size-3.5" aria-hidden="true" /> {children}
    </Link>
  );
}

const DIFFICULTY_TONE: Record<string, string> = {
  easy: 'bg-success/12 text-success border-success/25',
  medium: 'bg-warning/15 text-warning-foreground dark:text-warning border-warning/30',
  hard: 'bg-destructive/10 text-destructive border-destructive/25',
};

export function Difficulty({ level }: { level: string }) {
  return (
    <Badge variant="outline" className={cn('capitalize', DIFFICULTY_TONE[level])}>
      {level}
    </Badge>
  );
}

export function StatCard({ icon, label, value, hint, className }: { icon?: ReactNode; label: ReactNode; value: ReactNode; hint?: ReactNode; className?: string }) {
  return (
    <Card className={cn('gap-0', className)}>
      <CardContent className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{label}</p>
          <div className="mt-1 text-2xl font-semibold tracking-tight">{value}</div>
          {hint ? <div className="mt-0.5 text-xs text-muted-foreground">{hint}</div> : null}
        </div>
        {icon ? <span className="grid size-9 flex-none place-items-center rounded-lg bg-muted text-muted-foreground [&_svg]:size-4.5">{icon}</span> : null}
      </CardContent>
    </Card>
  );
}

/** Fade-and-rise entrance for page sections; staggered by index. */
export function Reveal({ children, index = 0, className }: { children: ReactNode; index?: number; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: Math.min(index, 8) * 0.05, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  );
}
