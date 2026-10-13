'use client';

import { useReportWebVitals } from 'next/web-vitals';

/**
 * Field performance: Core Web Vitals go to the API as anonymous samples (route pattern,
 * metric, value, device class; never the URL or the user), sent with sendBeacon when the
 * tab is hidden. The owner sees p75 per page in /admin.
 */
type Sample = { route: string; metric: string; value: number; device: 'mobile' | 'desktop' };

const METRICS = new Set(['LCP', 'INP', 'CLS', 'FCP', 'TTFB']);
const DYNAMIC: [RegExp, string][] = [
  [/^\/learn\/.+/, '/learn/[...concept]'],
  [/^\/problems\/[^/]+$/, '/problems/[id]'],
  [/^\/quiz\/.+/, '/quiz/[...activity]'],
];
const queue: Sample[] = [];
let listening = false;

function routeOf(path: string) {
  return DYNAMIC.find(([pattern]) => pattern.test(path))?.[1] ?? path;
}

function flush() {
  if (!queue.length) return;
  const samples = queue.splice(0, 10);
  // text/plain keeps this a simple request (no preflight); the API parses the JSON.
  const body = new Blob([JSON.stringify({ samples })], { type: 'text/plain' });
  try { navigator.sendBeacon?.('/api/v1/vitals', body); } catch { /* measurement is best effort */ }
  if (queue.length) flush();
}

export function WebVitals() {
  useReportWebVitals(metric => {
    if (!METRICS.has(metric.name)) return;
    queue.push({
      route: routeOf(window.location.pathname),
      metric: metric.name,
      value: metric.value,
      device: window.innerWidth < 768 ? 'mobile' : 'desktop',
    });
    if (!listening) {
      listening = true;
      document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') flush(); });
      window.addEventListener('pagehide', flush);
    }
    if (queue.length >= 10) flush();
  });
  return null;
}
