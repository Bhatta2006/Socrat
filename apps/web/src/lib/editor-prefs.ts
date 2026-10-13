'use client';

import { useCallback, useEffect, useState } from 'react';

export interface EditorPrefs {
  fontSize: number; // px, 12–20
  tabSize: 2 | 4;
  split: number; // share of the width given to the statement, 0.25–0.65
}

const KEY = 'socrat:editor';
export const DEFAULT_PREFS: EditorPrefs = { fontSize: 14, tabSize: 4, split: 5 / 12 };
const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

function sanitise(raw: Partial<EditorPrefs>): EditorPrefs {
  return {
    fontSize: clamp(Math.round(Number(raw.fontSize) || DEFAULT_PREFS.fontSize), 12, 20),
    tabSize: raw.tabSize === 2 ? 2 : 4,
    split: clamp(Number(raw.split) || DEFAULT_PREFS.split, 0.25, 0.65),
  };
}

/** Per-browser editor preferences (font size, indent width, pane split). */
export function useEditorPrefs(): [EditorPrefs, (patch: Partial<EditorPrefs>) => void] {
  const [prefs, setPrefs] = useState<EditorPrefs>(DEFAULT_PREFS);
  useEffect(() => {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored) setPrefs(sanitise(JSON.parse(stored) as Partial<EditorPrefs>));
    } catch { /* defaults */ }
  }, []);
  const update = useCallback((patch: Partial<EditorPrefs>) => {
    setPrefs(current => {
      const next = sanitise({ ...current, ...patch });
      try { localStorage.setItem(KEY, JSON.stringify(next)); } catch { /* per-viewer nicety only */ }
      return next;
    });
  }, []);
  return [prefs, update];
}
