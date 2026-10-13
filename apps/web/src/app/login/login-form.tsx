'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, ArrowUpRight, Check, Code2, Lightbulb, Route } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import type { Features } from '@/lib/types';
import { ErrorNote } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Spinner } from '@/components/ui/spinner';
import './login.css';

const PROMISES = [
  'A plan that adapts to what you actually know',
  'Lessons and problems in Python, C++ or Java',
  'A tutor that guides instead of giving answers away',
];

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path fill="#4285F4" d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.4h6.5a5.6 5.6 0 0 1-2.4 3.6v3h3.9c2.3-2.1 3.5-5.2 3.5-8.7z" />
      <path fill="#34A853" d="M12 24c3.2 0 6-1.1 8-2.9l-3.9-3c-1.1.7-2.5 1.2-4.1 1.2-3.1 0-5.8-2.1-6.7-5H1.3v3.1A12 12 0 0 0 12 24z" />
      <path fill="#FBBC05" d="M5.3 14.3a7.2 7.2 0 0 1 0-4.6V6.6H1.3a12 12 0 0 0 0 10.8l4-3.1z" />
      <path fill="#EA4335" d="M12 4.8c1.8 0 3.3.6 4.6 1.8l3.4-3.4A12 12 0 0 0 1.3 6.6l4 3.1c.9-2.9 3.6-4.9 6.7-4.9z" />
    </svg>
  );
}

export function LoginForm({ initialFeatures }: { initialFeatures: Features | null }) {
  const session = useSession();
  const { profile, loading, refresh } = session;
  // Sign-in options come with the HTML (fetched on the server) so the form paints at once.
  const features = initialFeatures ?? session.features;
  const router = useRouter();
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!loading && profile) router.replace(destination(profile, 'active') ?? '/today');
  }, [loading, profile, router]);

  async function devLogin(event: React.FormEvent) {
    event.preventDefault();
    const display = name.trim();
    if (!display) return;
    setBusy(true);
    setError('');
    try {
      const subject = display.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 64) || 'learner';
      await api.post('/auth/dev-login', { subject, display_name: display });
      const next = await refresh();
      router.replace(destination(next, 'active') ?? '/today');
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  return (
    <div className="login-page" data-theme="socrat-landing">
      <header className="login-header"><Link href="/" className="login-brand" aria-label="Socrat home"><span className="login-mark" aria-hidden="true"><i /><i /><i /></span>socrat<span>.</span></Link><Link href="/" className="login-back"><ArrowLeft size={16} aria-hidden="true" /> Back to home</Link></header>
      <div className="login-layout">
        <section className="login-story" aria-labelledby="login-story-title">
          <div className="login-banner">
            <p className="login-kicker"><span /> A little curiosity goes a long way</p>
            <h2 id="login-story-title">Learn today.<br />Think further<br />tomorrow.</h2>
            <p>Your next breakthrough starts with a question. Let’s find the answer together.</p>
            <div className="login-art" aria-hidden="true"><div className="login-torus" /><div className="login-coil"><span /><span /><span /><span /></div><div className="login-pebble" /></div>
            <span className="login-banner-note">Made for the way you learn <ArrowUpRight size={17} aria-hidden="true" /></span>
          </div>
          <div className="login-feature-grid"><article><Route size={21} aria-hidden="true" /><h3>A path of your own</h3><p>Start where you are.<br />Know what comes next.</p></article><article><Lightbulb size={21} aria-hidden="true" /><h3>Room to figure it out</h3><p>A helpful question.<br />A hint when you need it.</p></article></div>
          <div className="login-practice"><span className="login-practice-icon"><Code2 size={21} aria-hidden="true" /></span><div><h3>One idea. So many possibilities.</h3><p>Learn and practice in Python, C++ or Java.</p></div><span className="login-practice-shape" aria-hidden="true" /></div>
        </section>
        <section className="login-panel" aria-labelledby="login-title">
          <div className="login-form-content">
          <p className="login-kicker">Your next chapter</p>
          <h1 id="login-title">Welcome to Socrat</h1>
          <p className="login-description">Sign in or create your account in one step.<br />Your learning journey is waiting.</p>
          <div className="login-options">
          {/* The page renders before the session check returns (fast first paint); the
              sign-in options appear once the server says which are enabled. */}
          {!features ? (
            <div className="grid gap-4" role="status" aria-label="Loading sign-in options">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : null}
          {features?.oidc_login ? (
            <Button asChild variant="outline" size="lg" className="login-google daisy-btn">
              <a href="/api/v1/auth/login"><GoogleMark /> Continue with Google</a>
            </Button>
          ) : null}
          {features?.oidc_login && features?.dev_login ? (
            <div className="flex items-center gap-3 text-xs text-muted-foreground"><Separator className="flex-1" /> or, for local development <Separator className="flex-1" /></div>
          ) : null}
          {features?.dev_login ? (
            <form onSubmit={devLogin} className="grid gap-4">
              <Field>
                <FieldLabel htmlFor="login-name">Your name</FieldLabel>
                <Input id="login-name" className="login-input" placeholder="e.g. Ada" value={name} onChange={e => setName(e.target.value)} maxLength={80} autoComplete="given-name" aria-describedby="login-name-help" required autoFocus />
                <FieldDescription id="login-name-help">Development sign-in: the same name returns you to the same account.</FieldDescription>
              </Field>
              <Button size="lg" className="login-submit daisy-btn" disabled={busy || !name.trim()}>
                {busy ? <><Spinner /> Signing in…</> : <>Sign in <ArrowUpRight size={18} aria-hidden="true" /></>}
              </Button>
            </form>
          ) : null}
          {features && !features.oidc_login && !features.dev_login ? (
            <p className="text-center text-sm text-muted-foreground">Sign-in is not configured on this server.</p>
          ) : null}
          {error ? <ErrorNote message={error} /> : null}
          </div>
          <div className="login-reassurance"><p>Everything you need to keep going.</p><ul>{PROMISES.map(p => <li key={p}><Check size={15} aria-hidden="true" />{p}</li>)}</ul></div>
          <p className="login-footnote">A good question is always a good start.</p>
          </div>
          <footer className="login-panel-footer"><span>Learn to think. Then code.</span><span>Python / C++ / Java</span></footer>
        </section>
      </div>
      <footer className="login-footer"><span>© {new Date().getFullYear()} Socrat</span><span>Made for the curious.</span></footer>
    </div>
  );
}
