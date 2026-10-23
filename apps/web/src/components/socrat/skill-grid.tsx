import Link from 'next/link';
import { cn } from '@/lib/utils';
import { STATUS_LABEL, StatusIcon, type Status } from './status';
import type { MapNode } from './node-map';

const LEGEND: Status[] = ['mastered', 'practised', 'not_seen', 'review'];
const COLUMNS = 4;

/**
 * Compact skill map for Today: the skills of the current module in rows of four, labels above
 * the nodes, with a legend. Order in module only; the plan has no prerequisite edges.
 */
export function SkillGrid({ nodes, label }: { nodes: MapNode[]; label: string }) {
  const shown = nodes.slice(0, COLUMNS * 3);
  const columns = Math.max(1, Math.min(COLUMNS, shown.length)); // a short module spreads across the card
  const rows = Array.from({ length: Math.ceil(shown.length / columns) }, (_, r) => shown.slice(r * columns, (r + 1) * columns));
  const name = (n: MapNode) => `${n.title}: ${n.status === 'locked' ? 'Locked' : STATUS_LABEL[n.status]}${n.reviewDue ? ', review due' : ''}${n.current ? ', current' : ''}`;
  return (
    <div className="flex h-full flex-col">
      <ol className="grid gap-8 py-2" aria-label={`${label}, skill map`}>
        {rows.map((row, r) => (
          <li key={r}>
            <ol className="grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
              {row.map((n, i) => (
                <li key={n.id} className="relative flex flex-col items-center gap-2 px-1">
                  <span className={cn('line-clamp-2 min-h-10 text-center text-sm leading-5 text-muted-foreground', n.current && 'font-bold text-foreground')} aria-hidden="true">{n.title}</span>
                  {row.length > 1 ? (
                    <span
                      aria-hidden="true"
                      className={cn('absolute top-[calc(2.5rem+0.5rem+26px)] h-px bg-border-strong', i === 0 ? 'right-0 left-1/2' : i === row.length - 1 ? 'right-1/2 left-0' : 'inset-x-0')}
                    />
                  ) : null}
                  <Link href={n.href} aria-label={name(n)} title={name(n)} className="relative z-10 grid size-13 place-items-center rounded-full bg-card">
                    <StatusIcon status={n.reviewDue && n.status !== 'locked' ? 'review' : n.status} size={44} />
                  </Link>
                </li>
              ))}
            </ol>
          </li>
        ))}
      </ol>
      <ul className="mt-auto flex flex-wrap gap-x-5 gap-y-2 border-t pt-4 text-[13px] [&]:mt-auto text-muted-foreground" aria-label="Legend">
        {LEGEND.map(s => (
          <li key={s} className="inline-flex items-center gap-2"><StatusIcon status={s} size={20} />{STATUS_LABEL[s]}</li>
        ))}
      </ul>
    </div>
  );
}
