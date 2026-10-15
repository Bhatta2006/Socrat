import Link from 'next/link';
import type { ComponentProps } from 'react';
import { cn } from '@/lib/utils';

/**
 * Round floating arrow on hero cards: ink on violet, violet on neutral. 56 px, 44 px compact.
 * Always has an accessible name; the visible title of its card says where it goes.
 */
export function ArrowButton({ href, label, onColor = true, compact = false, className, transitionTypes }: {
  href: string; label: string; onColor?: boolean; compact?: boolean; className?: string; transitionTypes?: ComponentProps<typeof Link>['transitionTypes'];
}) {
  return (
    <Link
      href={href}
      aria-label={label}
      transitionTypes={transitionTypes}
      className={cn(
        'group/arrow grid flex-none place-items-center rounded-full shadow-floating transition-transform duration-200 ease-[var(--ease-soft)] active:scale-[0.98]',
        compact ? 'size-11' : 'size-14',
        onColor ? 'bg-ink text-ink-foreground' : 'bg-primary text-primary-foreground',
        className,
      )}
    >
      <svg viewBox="0 0 24 24" className="size-6 transition-transform duration-200 ease-[var(--ease-soft)] group-hover/arrow:translate-x-0.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M5 12h14M13 6l6 6-6 6" />
      </svg>
    </Link>
  );
}
