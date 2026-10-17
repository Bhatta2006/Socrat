'use client';

/**
 * Installing Socrat as an app. Chromium browsers fire `beforeinstallprompt` once, early, so a
 * module-level listener keeps it until a button asks for it. Safari on iOS has no prompt; the
 * button explains Share, then Add to Home Screen, instead.
 */
import { useEffect, useState } from 'react';

interface InstallPrompt extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

let deferred: InstallPrompt | null = null;
const listeners = new Set<() => void>();
const notify = () => listeners.forEach(fn => fn());

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    deferred = event as InstallPrompt;
    notify();
  });
  window.addEventListener('appinstalled', () => { deferred = null; notify(); });
}

export function registerServiceWorker() {
  if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
  if (process.env.NODE_ENV !== 'production' && !process.env.NEXT_PUBLIC_SW_IN_DEV) return;
  navigator.serviceWorker.register('/sw.js', { scope: '/', updateViaCache: 'none' }).catch(() => undefined);
}

export type InstallState = 'installed' | 'prompt' | 'ios' | 'unsupported';

function current(): InstallState {
  if (typeof window === 'undefined') return 'unsupported';
  const standalone = window.matchMedia('(display-mode: standalone)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true;
  if (standalone) return 'installed';
  if (deferred) return 'prompt';
  const ua = navigator.userAgent;
  const ios = /iPad|iPhone|iPod/.test(ua) || (ua.includes('Macintosh') && navigator.maxTouchPoints > 1);
  return ios ? 'ios' : 'unsupported';
}

export function useInstall() {
  const [state, setState] = useState<InstallState>('unsupported');
  useEffect(() => {
    const update = () => setState(current());
    update();
    listeners.add(update);
    return () => { listeners.delete(update); };
  }, []);
  async function install(): Promise<boolean> {
    if (!deferred) return false;
    const prompt = deferred;
    deferred = null;
    await prompt.prompt();
    const choice = await prompt.userChoice;
    notify();
    return choice.outcome === 'accepted';
  }
  return { state, install };
}
