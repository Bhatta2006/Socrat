'use client';

import Link from 'next/link';
import type { ReactNode } from 'react';
import { Check, RotateCw } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Illustration } from './illustration';
import { StatusIcon } from './status';

/** Coral triangle used for every error and attention message. */
export function AttentionIcon({ className, size = 20 }: { className?: string; size?: number }) {
  return <StatusIcon status="needs_practice" size={size} className={className} />;
}

/** Nothing yet, or nothing matches: one headline, one sentence, one action. */
export function EmptyState({ title, children, action, className, illustration = true, as: Heading = 'h2' }: {
  title: string; children?: ReactNode; action?: ReactNode; className?: string; illustration?: boolean; as?: 'h2' | 'h3';
}) {
  return (
    <div className={cn('grid justify-items-center gap-3 rounded-card border border-dashed border-border-strong px-6 py-10 text-center', className)}>
      {illustration ? <Illustration name="empty" className="size-24" /> : null}
      <Heading className="font-display text-xl font-bold tracking-[-0.02em]">{title}</Heading>
      {children ? <div className="max-w-md text-[15px] text-muted-foreground text-pretty">{children}</div> : null}
      {action ? <div className="mt-1">{action}</div> : null}
    </div>
  );
}

/** Inline error: what happened, what to do, and a retry. Never toast-only. */
export function ErrorState({ message, retry, title = 'Something went wrong', className, actions }: {
  message: ReactNode; retry?: () => void; title?: string; className?: string; actions?: ReactNode;
}) {
  return (
    <div role="alert" className={cn('my-4 flex flex-wrap items-start gap-3 rounded-[20px] border border-attention bg-card px-4 py-4', className)}>
      <AttentionIcon className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        <div className="mt-0.5 text-[15px] text-muted-foreground">{message}</div>
      </div>
      {retry || actions ? (
        <div className="flex flex-wrap gap-2">
          {actions}
          {retry ? <Button variant="outline" size="sm" onClick={retry}><RotateCw data-icon="inline-start" /> Try again</Button> : null}
        </div>
      ) : null}
    </div>
  );
}

/** Content gated by a checkpoint: what unlocks it and a link to that thing. */
export function LockedState({ title, children, href, action = 'Go to checkpoint', className }: {
  title: string; children?: ReactNode; href?: string; action?: string; className?: string;
}) {
  return (
    <div className={cn('flex flex-col items-start gap-4 rounded-card border border-border-strong px-5 py-5 sm:flex-row sm:items-center', className)}>
      <StatusIcon status="locked" size={32} />
      <div className="w-full min-w-0 flex-1">
        <p className="font-display text-lg font-bold tracking-[-0.02em]">{title}</p>
        {children ? <div className="mt-0.5 text-[15px] text-muted-foreground">{children}</div> : null}
      </div>
      {href ? <Button asChild variant="outline"><Link href={href}>{action}</Link></Button> : null}
    </div>
  );
}

/** Plain confirmation with the next action. No celebration. */
export function SuccessLine({ children, action, className }: { children: ReactNode; action?: ReactNode; className?: string }) {
  return (
    <div role="status" className={cn('flex flex-wrap items-center gap-3 text-[15px]', className)}>
      <span className="grid size-7 place-items-center rounded-full bg-cream text-cream-foreground"><Check className="size-4" aria-hidden="true" /></span>
      <span className="font-semibold">{children}</span>
      {action}
    </div>
  );
}
