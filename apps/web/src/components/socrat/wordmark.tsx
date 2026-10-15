import { cn } from '@/lib/utils';

/** The mark: a geometric S from two offset half-discs, brand over lime. Minimum 24 px. */
export function Mark({ size = 28, className }: { size?: number; className?: string }) {
  return (
    <svg viewBox="0 0 32 32" width={Math.max(24, size)} height={Math.max(24, size)} className={cn('flex-none', className)} aria-hidden="true">
      <path d="M16 3a6.5 6.5 0 0 0 0 13Z" fill="var(--violet)" />
      <path d="M16 16a6.5 6.5 0 0 1 0 13Z" fill="var(--mark-cream)" />
      <circle cx="16" cy="16" r="12.25" fill="none" stroke="var(--border-strong)" strokeWidth="1.5" />
    </svg>
  );
}

/** Wordmark: the mark plus "Socrat" in the display face. Used on every surface and the favicon. */
export function Wordmark({ className, compact = false, size = 28 }: { className?: string; compact?: boolean; size?: number }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <Mark size={size} />
      {compact ? <span className="sr-only">Socrat</span> : <span className="font-display text-[22px] leading-none font-bold tracking-[-0.03em]">Socrat</span>}
    </span>
  );
}
