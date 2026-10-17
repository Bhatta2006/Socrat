'use client';

import { useEffect } from 'react';
import { reportError } from '@/lib/report-error';

/** Reports uncaught errors and unhandled promise rejections to /admin (see report-error.ts). */
export function ErrorReporter() {
  useEffect(() => {
    const onError = (event: ErrorEvent) => {
      // Cross-origin script errors arrive without detail; they are not actionable.
      if (event.message === 'Script error.' && !event.error) return;
      reportError('error', event.error ?? event.message);
    };
    const onRejection = (event: PromiseRejectionEvent) => reportError('unhandledrejection', event.reason);
    window.addEventListener('error', onError);
    window.addEventListener('unhandledrejection', onRejection);
    return () => {
      window.removeEventListener('error', onError);
      window.removeEventListener('unhandledrejection', onRejection);
    };
  }, []);
  return null;
}
