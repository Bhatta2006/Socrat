import { cn } from '@/lib/utils';

/**
 * Seven days ending today; today sits in a violet pill with a bold number. A dot marks study
 * activity only where the data says so (today, from `studied_today`).
 */
export function WeekStrip({ studiedToday, className }: { studiedToday: boolean; className?: string }) {
  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date;
  });
  return (
    <ol className={cn('grid grid-cols-7 gap-1', className)} aria-label="This week">
      {days.map((date, i) => {
        const today = i === 6;
        const label = date.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
        return (
          <li key={i} className="grid justify-items-center gap-1.5" aria-current={today ? 'date' : undefined}>
            <span className="text-xs font-medium text-muted-foreground" aria-hidden="true">{date.toLocaleDateString(undefined, { weekday: 'narrow' })}</span>
            <span
              className={cn('grid h-10 w-full max-w-11 place-items-center rounded-full text-[15px] font-medium tabular-nums', today ? 'bg-primary font-bold text-primary-foreground' : 'text-foreground')}
              aria-label={`${label}${today ? (studiedToday ? ', studied' : ', today') : ''}`}
            >
              {date.getDate()}
            </span>
            <span className={cn('size-1.5 rounded-full', today && studiedToday ? 'bg-foreground' : 'bg-transparent')} aria-hidden="true" />
          </li>
        );
      })}
    </ol>
  );
}
