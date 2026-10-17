/**
 * Browser crash reports go to our own API (no third-party script): the message, a trimmed
 * stack and the page path, never the query string, page content or the learner's code.
 */
type Kind = 'error' | 'unhandledrejection' | 'render' | 'runner';

const seen = new Set<string>();

export function reportError(kind: Kind, error: unknown) {
  try {
    const err = error instanceof Error ? error : new Error(typeof error === 'string' ? error : 'Unknown error');
    const message = (err.message || err.name || 'Unknown error').slice(0, 500);
    const key = `${kind}|${message}`;
    // One report per distinct error per page load is enough to count it.
    if (seen.has(key) || seen.size > 20) return;
    seen.add(key);
    const body = JSON.stringify({
      kind,
      message,
      stack: (err.stack ?? '').slice(0, 4000),
      route: window.location.pathname.slice(0, 120),
      release: process.env.NEXT_PUBLIC_RELEASE ?? '',
    });
    // text/plain keeps it a simple request (no preflight); the API parses the JSON.
    const blob = new Blob([body], { type: 'text/plain' });
    if (!navigator.sendBeacon?.('/api/v1/client-errors', blob)) {
      void fetch('/api/v1/client-errors', { method: 'POST', body: blob, keepalive: true }).catch(() => undefined);
    }
  } catch {
    /* reporting is best effort */
  }
}
