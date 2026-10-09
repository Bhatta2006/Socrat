import type { ActivityKind } from './types';

/** Activity ids look like `lesson:zero:variables-and-types`; URLs use path segments. */
export function activityHref(id: string): string {
  const [kind, ...rest] = id.split(':');
  if (kind === 'lesson') return `/learn/${rest.join('/')}`;
  if (kind === 'problem') return `/problems/${rest.join('/')}`;
  return `/quiz/${kind}/${rest.join('/')}`;
}

export function conceptHref(qualified: string): string {
  return `/learn/${qualified.split(':').join('/')}`;
}

export function joinSegments(value: string | string[] | undefined): string {
  return Array.isArray(value) ? value.map(decodeURIComponent).join(':') : decodeURIComponent(value ?? '');
}

export const KIND_LABEL: Record<ActivityKind, string> = {
  lesson: 'Lesson',
  quiz: 'Concept check',
  problem: 'Practice',
  checkpoint: 'Checkpoint',
  review: 'Review',
  remedial: 'Refresher',
};

export const LANGUAGE_LABEL = { python: 'Python', cpp: 'C++', java: 'Java' } as const;

export const BAND_LABEL = {
  not_started: 'Not started',
  needs_practice: 'Needs practice',
  developing: 'Developing',
  likely_known: 'Likely known',
  strong: 'Strong',
} as const;

export const PACE_LABEL = { support: 'Extra support', steady: 'Steady', fast: 'Fast track' } as const;

export function formatDate(iso: string, options: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }) {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, options);
}

export function formatStamp(seconds: number) {
  return new Date(seconds * 1000).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

export function hours(minutes: number) {
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h} h ${m} min` : `${h} h`;
}
