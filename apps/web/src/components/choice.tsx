'use client';

import type { ComponentProps, ReactNode } from 'react';
import { Check, X } from 'lucide-react';
import { cn } from '@/lib/utils';

type Tone = 'idle' | 'correct' | 'wrong';

/**
 * A large selectable card. Use `role="radio"` + `aria-checked` for answers, or
 * `aria-pressed` for setup choices. Correct/wrong tones give instant, unmistakable feedback.
 */
export function Choice({
  selected = false,
  tone = 'idle',
  marker,
  icon,
  children,
  className,
  ...props
}: ComponentProps<'button'> & { selected?: boolean; tone?: Tone; marker?: ReactNode; icon?: ReactNode }) {
  return (
    <button
      type="button"
      data-selected={selected || undefined}
      data-tone={tone}
      className={cn(
        'group/choice flex w-full items-start gap-3 rounded-xl border bg-card p-4 text-left transition-all outline-none',
        'hover:border-primary/50 hover:bg-accent/40 focus-visible:ring-3 focus-visible:ring-ring/50',
        'data-[selected]:border-primary data-[selected]:bg-primary/5 data-[selected]:ring-1 data-[selected]:ring-primary',
        'disabled:cursor-default disabled:hover:bg-card',
        tone === 'correct' && 'animate-pop border-success bg-success/10 ring-1 ring-success hover:bg-success/10',
        tone === 'wrong' && 'animate-shake border-destructive bg-destructive/8 ring-1 ring-destructive hover:bg-destructive/8',
        className,
      )}
      {...props}
    >
      {marker !== undefined ? (
        <span
          className={cn(
            'grid size-7 flex-none place-items-center rounded-lg border text-xs font-semibold text-muted-foreground transition-colors',
            'group-data-[selected]/choice:border-primary group-data-[selected]/choice:bg-primary group-data-[selected]/choice:text-primary-foreground',
            tone === 'correct' && 'border-success bg-success text-success-foreground',
            tone === 'wrong' && 'border-destructive bg-destructive text-white',
          )}
          aria-hidden="true"
        >
          {tone === 'correct' ? <Check className="size-4" /> : tone === 'wrong' ? <X className="size-4" /> : marker}
        </span>
      ) : null}
      {icon ? <span className="grid size-10 flex-none place-items-center rounded-lg bg-primary/10 text-primary [&_svg]:size-5">{icon}</span> : null}
      <span className="min-w-0 flex-1">{children}</span>
    </button>
  );
}

/** Pill toggle used for minutes and weekdays. */
export function Pill({ pressed, className, ...props }: ComponentProps<'button'> & { pressed: boolean }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      className={cn(
        'h-9 rounded-full border bg-card px-4 text-sm font-medium transition-all hover:border-primary/50',
        'aria-pressed:border-primary aria-pressed:bg-primary aria-pressed:text-primary-foreground aria-pressed:shadow-sm aria-pressed:shadow-primary/20',
        'outline-none focus-visible:ring-3 focus-visible:ring-ring/50',
        className,
      )}
      {...props}
    />
  );
}
