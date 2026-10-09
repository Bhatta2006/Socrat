import confetti from 'canvas-confetti';

/** A short burst for real milestones (goal met, problem solved). Silent with reduced motion. */
export function celebrate(intensity: 'small' | 'big' = 'small') {
  if (typeof window === 'undefined') return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const colors = ['#10b981', '#34d399', '#f59e0b', '#60a5fa'];
  if (intensity === 'small') {
    confetti({ particleCount: 70, spread: 70, origin: { y: 0.7 }, colors, disableForReducedMotion: true });
    return;
  }
  const end = Date.now() + 600;
  (function frame() {
    confetti({ particleCount: 5, angle: 60, spread: 60, origin: { x: 0 }, colors, disableForReducedMotion: true });
    confetti({ particleCount: 5, angle: 120, spread: 60, origin: { x: 1 }, colors, disableForReducedMotion: true });
    if (Date.now() < end) requestAnimationFrame(frame);
  })();
}

/** Celebrate a milestone at most once per key (e.g. once per day for the daily goal). */
export function celebrateOnce(key: string, intensity: 'small' | 'big' = 'small') {
  try {
    if (localStorage.getItem(key)) return;
    localStorage.setItem(key, '1');
  } catch {
    return;
  }
  celebrate(intensity);
}
