'use client';

import Link from 'next/link';
import { useState } from 'react';
import { Check, ExternalLink, Star } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import type { ExternalProblem, Level, PracticeStatus } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Difficulty } from './common';

const PLATFORM_TONE: Record<string, string> = {
  Socrat: 'border-primary/30 bg-primary/10 text-primary',
  LeetCode: 'border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300',
  CSES: 'border-sky-500/30 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  Codeforces: 'border-rose-500/30 bg-rose-500/10 text-rose-700 dark:text-rose-300',
};

export function PlatformTag({ platform }: { platform: string }) {
  return <Badge variant="outline" className={cn('font-medium', PLATFORM_TONE[platform])}>{platform}</Badge>;
}

/** Difficulty label plus the rating when the platform provides one. */
export function Level({ problem }: { problem: Pick<ExternalProblem, 'difficulty' | 'rating'> }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <Difficulty level={problem.difficulty} />
      {problem.rating ? <span className="font-mono text-xs text-muted-foreground tabular-nums" title="Codeforces rating">{problem.rating}</span> : null}
    </span>
  );
}

/**
 * A problem shown by name. External problems open on the official site in a new tab and
 * are recorded as attempted; the address itself is never displayed.
 */
export function ProblemName({
  problem,
  className = '',
  onOpened,
}: {
  problem: Pick<ExternalProblem, 'id' | 'title' | 'url' | 'platform'>;
  className?: string;
  onOpened?: () => void;
}) {
  const classes = cn('font-medium underline-offset-4 transition-colors hover:text-primary hover:underline', className);
  if (problem.url.startsWith('/')) return <Link href={problem.url} className={classes}>{problem.title}</Link>;
  return (
    <a
      href={problem.url}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(classes, 'group/link inline-flex items-center gap-1')}
      onClick={() => {
        api.post(`/library/problems/${problem.id}/opened`).then(() => onOpened?.()).catch(() => undefined);
      }}
    >
      {problem.title}
      <span className="sr-only"> (opens on {problem.platform} in a new tab)</span>
      <ExternalLink aria-hidden="true" className="size-3 text-muted-foreground opacity-0 transition-opacity group-hover/link:opacity-100" />
    </a>
  );
}

export function StatusControl({
  id,
  status,
  bookmarked,
  onChange,
  compact = false,
}: {
  id: string;
  status: PracticeStatus | null;
  bookmarked: boolean;
  onChange?: (next: { status: PracticeStatus | null; bookmarked: boolean }) => void;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  if (id.startsWith('socrat:')) return null; // judged in the app; status comes from submissions
  async function save(body: { status?: PracticeStatus; bookmarked?: boolean }) {
    setBusy(true);
    try {
      const result = await api.put<{ status: PracticeStatus; bookmarked: boolean }>(`/library/problems/${id}`, body);
      onChange?.(result);
      if (body.status === 'solved') toast.success('Marked solved', { description: 'Counted toward your mastery on this concept.' });
      else if (body.bookmarked) toast.success('Saved to your list');
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setBusy(false);
    }
  }
  const solved = status === 'solved';
  return (
    <span className="inline-flex items-center gap-1">
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            type="button"
            size={compact ? 'icon-sm' : 'sm'}
            variant={solved ? 'default' : 'ghost'}
            className={cn(solved && 'bg-success text-success-foreground hover:bg-success/90')}
            disabled={busy}
            aria-pressed={solved}
            onClick={() => save({ status: solved ? 'attempted' : 'solved' })}
          >
            <Check />
            {compact ? <span className="sr-only">{solved ? 'Solved' : 'Mark as solved'}</span> : solved ? 'Solved' : 'Mark solved'}
          </Button>
        </TooltipTrigger>
        <TooltipContent>{solved ? 'Solved — click to undo' : 'Mark as solved'}</TooltipContent>
      </Tooltip>
      <Button
        type="button"
        size="icon-sm"
        variant="ghost"
        className={cn(bookmarked ? 'text-amber-500' : 'text-muted-foreground')}
        disabled={busy}
        aria-pressed={bookmarked}
        aria-label={bookmarked ? 'Remove from my list' : 'Save to my list'}
        onClick={() => save({ bookmarked: !bookmarked })}
      >
        <Star className={cn(bookmarked && 'fill-current')} />
      </Button>
    </span>
  );
}

export function LevelCard({ level, solved }: { level: Level; solved?: number }) {
  return (
    <div>
      <p className="text-xs font-medium text-muted-foreground">Practice level</p>
      <div className="mt-1 flex items-baseline gap-2">
        <span className="text-2xl font-semibold tracking-tight">{level.name}</span>
        <span className="font-mono text-sm text-muted-foreground tabular-nums">~{level.rating}</span>
      </div>
      {level.next_name ? (
        <>
          <Progress value={level.progress * 100} className="mt-3 h-1.5" aria-label={`Progress to ${level.next_name}`} />
          <p className="mt-1.5 text-xs text-muted-foreground">
            {Math.round(level.progress * 100)}% of the way to <span className="font-medium text-foreground">{level.next_name}</span>
            {solved ? ` · ${solved} solved` : ''}
          </p>
        </>
      ) : null}
    </div>
  );
}
