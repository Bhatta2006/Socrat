'use client';

import { useCallback, useEffect, useState } from 'react';

const KEY = 'socrat:reduce-motion';

/** Runs before first paint (inline in the root layout) so the setting never flashes motion. */
export const REDUCE_MOTION_SCRIPT = `try{if(localStorage.getItem('${KEY}')==='true')document.documentElement.dataset.reduceMotion='true'}catch(e){}`;

/** True when the system asks for less motion or the learner turned it off in Settings. */
export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined') return false;
  return document.documentElement.dataset.reduceMotion === 'true' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** The in-app reduce-motion setting (per browser), and whether motion is reduced overall. */
export function useReducedMotion(): { setting: boolean; reduced: boolean; set(value: boolean): void } {
  const [setting, setSetting] = useState(false);
  const [system, setSystem] = useState(false);
  useEffect(() => {
    setSetting(document.documentElement.dataset.reduceMotion === 'true');
    const query = window.matchMedia('(prefers-reduced-motion: reduce)');
    setSystem(query.matches);
    const update = () => setSystem(query.matches);
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);
  const set = useCallback((value: boolean) => {
    setSetting(value);
    if (value) document.documentElement.dataset.reduceMotion = 'true';
    else delete document.documentElement.dataset.reduceMotion;
    try { localStorage.setItem(KEY, String(value)); } catch { /* per-viewer nicety only */ }
  }, []);
  return { setting, reduced: setting || system, set };
}
