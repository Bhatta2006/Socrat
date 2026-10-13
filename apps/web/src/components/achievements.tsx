'use client';

import { useEffect, useState } from 'react';
import {
  BookOpen, Brain, CalendarCheck, CircleCheck, ClipboardCheck, Crown, Flame, GraduationCap,
  ListChecks, Medal, Mountain, ShieldCheck, Zap, type LucideIcon,
} from 'lucide-react';
import type { Achievement } from '@/lib/types';
import { cn } from '@/lib/utils';
import { celebrate } from '@/components/celebrate';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

const ICON: Record<string, LucideIcon> = {
  'first-lesson': BookOpen,
  'first-solve': CircleCheck,
  'hard-solve': Mountain,
  'solved-10': ListChecks,
  'independent-10': Brain,
  'solved-50': Medal,
  'solved-100': Crown,
  'first-gate': ShieldCheck,
  'course-cleared': GraduationCap,
  'weekly-check': ClipboardCheck,
  'clean-sprint': Zap,
  'streak-7': Flame,
  'streak-30': CalendarCheck,
};
const SEEN_KEY = 'socrat:achievements-seen';

function readSeen(): Set<string> | null {
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    return raw ? new Set(JSON.parse(raw) as string[]) : null;
  } catch {
    return new Set();
  }
}

/** Earned first (newest first), then the ones closest to done: the next goal stays in view. */
function ordered(items: Achievement[]) {
  return [...items].sort((a, b) => {
    if (a.earned !== b.earned) return a.earned ? -1 : 1;
    if (a.earned) return (b.earned_at ?? 0) - (a.earned_at ?? 0);
    return b.value / Math.max(1, b.goal) - a.value / Math.max(1, a.goal);
  });
}

export function Achievements({ items }: { items: Achievement[] }) {
  const [fresh, setFresh] = useState<Set<string>>(new Set());
  const [all, setAll] = useState(false);

  useEffect(() => {
    const earned = items.filter(a => a.earned).map(a => a.id);
    const seen = readSeen();
    // First visit: everything already earned is history, not news.
    const news = seen ? earned.filter(id => !seen.has(id)) : [];
    try { localStorage.setItem(SEEN_KEY, JSON.stringify(earned)); } catch { /* per-viewer nicety only */ }
    if (news.length) {
      setFresh(new Set(news));
      celebrate('small');
    }
  }, [items]);

  const earnedCount = items.filter(a => a.earned).length;
  // Phones show what is earned plus the three nearest goals; wider screens show everything.
  const visible = earnedCount + 3;
  return (
    <Card className="mb-8" aria-labelledby="achievements-heading">
      <CardHeader>
        <CardTitle as="h2" id="achievements-heading">Achievements</CardTitle>
        <CardDescription>{earnedCount} of {items.length} earned · milestones for real skill, not time spent</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {ordered(items).map((a, i) => {
            const Icon = ICON[a.id] ?? Medal;
            return (
              <li
                key={a.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-3 transition-colors',
                  a.earned ? 'bg-card' : 'bg-muted/40',
                  fresh.has(a.id) && 'border-primary ring-2 ring-primary/20',
                  !all && i >= visible && 'max-sm:hidden',
                )}
              >
                <span
                  className={cn(
                    'flex size-9 shrink-0 items-center justify-center rounded-full',
                    a.earned ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground',
                  )}
                  aria-hidden="true"
                >
                  <Icon className="size-4" />
                </span>
                <span className="grid min-w-0 flex-1 gap-1">
                  <span className="flex items-center gap-2">
                    <span className={cn('truncate text-sm font-medium', !a.earned && 'text-muted-foreground')}>{a.title}</span>
                    {fresh.has(a.id) ? <Badge className="h-5 px-1.5 text-[10px]">New</Badge> : null}
                  </span>
                  <span className="text-xs text-muted-foreground">{a.description}</span>
                  {a.earned ? (
                    <span className="text-xs font-medium text-success">
                      {a.earned_at ? `Earned ${new Date(a.earned_at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}` : 'Earned'}
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Progress value={(100 * a.value) / Math.max(1, a.goal)} className="h-1.5" aria-label={`${a.title}: ${a.value} of ${a.goal}`} />
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">{a.value}/{a.goal}</span>
                    </span>
                  )}
                </span>
              </li>
            );
          })}
        </ul>
        {items.length > visible ? (
          <Button variant="outline" size="sm" className="mt-3 w-full sm:hidden" onClick={() => setAll(v => !v)} aria-expanded={all}>
            {all ? 'Show fewer' : `Show all ${items.length}`}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}
