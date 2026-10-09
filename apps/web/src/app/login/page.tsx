'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, Sparkles } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { destination, useSession } from '@/lib/session';
import { ErrorNote, Loading } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Spinner } from '@/components/ui/spinner';

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

export default function Login() {
  const { profile, features, loading, refresh } = useSession();
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

  if (loading || profile) return <Loading />;
  return (
    <div className="mx-auto grid min-h-[calc(100dvh-3.5rem)] max-w-6xl items-center gap-12 px-4 py-10 sm:px-6 md:grid-cols-2">
      <div className="hidden md:block">
        <span className="mb-6 grid size-11 place-items-center rounded-xl bg-primary text-primary-foreground shadow-lg shadow-primary/25">
          <Sparkles className="size-5" />
        </span>
        <h1 className="text-4xl font-semibold tracking-tight text-balance">Pick up exactly where you left off.</h1>
        <p className="mt-4 max-w-md text-lg text-muted-foreground">Your plan, progress and code drafts are saved to your account.</p>
        <ul className="mt-8 grid gap-3">
          {PROMISES.map(p => (
            <li key={p} className="flex items-center gap-2.5 text-sm"><CheckCircle2 className="size-4 text-primary" /> {p}</li>
          ))}
        </ul>
      </div>
      <Card className="mx-auto w-full max-w-md shadow-xl shadow-foreground/5">
        <CardHeader className="text-center">
          <CardTitle className="text-xl">Welcome to Socrat</CardTitle>
          <CardDescription>Sign in or create your account in one step.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          {features?.oidc_login ? (
            <Button asChild variant="outline" size="lg" className="h-10 w-full">
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
                <Input id="login-name" className="h-10" value={name} onChange={e => setName(e.target.value)} maxLength={80} autoComplete="given-name" required autoFocus />
                <FieldDescription>Development sign-in: the same name returns you to the same account.</FieldDescription>
              </Field>
              <Button size="lg" className="h-10 w-full" disabled={busy || !name.trim()}>
                {busy ? <><Spinner /> Signing in…</> : 'Sign in'}
              </Button>
            </form>
          ) : null}
          {features && !features.oidc_login && !features.dev_login ? (
            <p className="text-center text-sm text-muted-foreground">Sign-in is not configured on this server.</p>
          ) : null}
          {error ? <ErrorNote message={error} /> : null}
          <p className="text-center text-xs text-muted-foreground">By continuing you agree to learn by thinking, not copying.</p>
        </CardContent>
      </Card>
    </div>
  );
}
