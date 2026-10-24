import { cn } from '@/lib/utils';

/** The mark: the Socrat app icon (public/icons). Minimum 24 px. */
export function Mark({ size = 28, className }: { size?: number; className?: string }) {
  const px = Math.max(24, size);
  return (
    // eslint-disable-next-line @next/next/no-img-element -- a fixed-size local asset; no loader needed
    <img src="/icons/icon-192.png" width={px} height={px} alt="" aria-hidden="true" draggable={false} className={cn('flex-none rounded-[22%]', className)} />
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
