'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';

type Profile = {
  id: string;
  display_name: string;
  timezone: string;
  adult_confirmed: boolean;
  csrf_token: string;
};

type Features = { dev_login: boolean; oidc_login: boolean };

async function jsonRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: 'same-origin' });
  if (!response.ok) throw new Error(String(response.status));
  return response.status === 204 ? (undefined as T) : response.json();
}

function validTimezone(timezone: string) {
  try {
    new Intl.DateTimeFormat('en', { timeZone: timezone }).format();
    return true;
  } catch {
    return false;
  }
}

export default function Workspace() {
  const [features, setFeatures] = useState<Features | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [timezone, setTimezone] = useState('UTC');
  const [adultConfirmed, setAdultConfirmed] = useState(false);
  const [pending, setPending] = useState(true);
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);

  const loadProfile = useCallback(async () => {
    try {
      const value = await jsonRequest<Profile>('/api/v1/me');
      setProfile(value);
      setDisplayName(value.display_name);
      setTimezone(value.timezone);
      setAdultConfirmed(value.adult_confirmed);
    } catch (error) {
      if ((error as Error).message !== '401') setMessage('The workspace is temporarily unavailable.');
      setProfile(null);
    } finally {
      setPending(false);
    }
  }, []);

  useEffect(() => {
    Promise.all([
      jsonRequest<Features>('/api/v1/features').then(setFeatures),
      loadProfile(),
    ]).catch(() => {
      setIsError(true);
      setMessage('The workspace is temporarily unavailable.');
      setPending(false);
    });
  }, [loadProfile]);

  async function localLogin() {
    setPending(true);
    setMessage('');
    try {
      await jsonRequest('/api/v1/auth/dev-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ subject: 'local-learner' }),
      });
      await loadProfile();
    } catch {
      setIsError(true);
      setMessage('Sign-in failed. Please try again.');
      setPending(false);
    }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setMessage('');
    if (!validTimezone(timezone)) {
      setIsError(true);
      setMessage('Enter a valid timezone, such as Asia/Kolkata.');
      return;
    }
    if (!profile) return;
    setPending(true);
    try {
      const value = await jsonRequest<Profile>('/api/v1/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile.csrf_token },
        body: JSON.stringify({ display_name: displayName, timezone, adult_confirmed: adultConfirmed }),
      });
      setProfile(value);
      setIsError(false);
      setMessage('Profile saved.');
    } catch {
      setIsError(true);
      setMessage('Profile could not be saved. Review the fields and try again.');
    } finally {
      setPending(false);
    }
  }

  async function logout() {
    if (!profile) return;
    setPending(true);
    try {
      await jsonRequest('/api/v1/auth/logout', {
        method: 'POST',
        headers: { 'X-CSRF-Token': profile.csrf_token },
      });
      setProfile(null);
      setMessage('');
    } catch {
      setIsError(true);
      setMessage('Sign-out failed. Please try again.');
    } finally {
      setPending(false);
    }
  }

  return (
    <section id="workspace" className="card border border-base-300 bg-base-100 shadow-none" aria-busy={pending}>
      <div className="card-body gap-6 p-6 sm:p-8">
        {pending && !features ? (
          <p role="status" className="text-sm text-base-content/60">Checking workspace…</p>
        ) : profile ? (
          <>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-base-content/60">Account foundation</p>
              <h2 className="mt-2 text-2xl font-bold">Your profile</h2>
              <p className="mt-2 text-sm leading-6 text-base-content/65">Only the identity and preferences layer is active in M1.</p>
            </div>
            <form className="space-y-5" onSubmit={save} noValidate>
              <fieldset className="fieldset">
                <legend className="fieldset-legend">Display name</legend>
                <input className="input w-full" aria-label="Display name" value={displayName} maxLength={80}
                  onChange={(event) => setDisplayName(event.target.value)} required />
              </fieldset>
              <label className="label cursor-pointer justify-start gap-3">
                <input className="checkbox" type="checkbox" checked={adultConfirmed}
                  onChange={(event) => setAdultConfirmed(event.target.checked)} />
                <span>I confirm I meet the age requirement for the future learner beta.</span>
              </label>
              <fieldset className="fieldset">
                <legend className="fieldset-legend">Timezone</legend>
                <input className="input w-full" aria-label="Timezone" value={timezone} maxLength={64}
                  onChange={(event) => setTimezone(event.target.value)} required />
                <p className="label">Use an IANA timezone, for example Asia/Kolkata.</p>
              </fieldset>
              {message && <div className={`alert ${isError ? 'alert-error' : 'alert-success'}`} role={isError ? 'alert' : 'status'}>{message}</div>}
              <div className="flex flex-col gap-3 sm:flex-row">
                <button className="btn btn-neutral flex-1" type="submit" disabled={pending || !displayName.trim()}>Save profile</button>
                <button className="btn" type="button" onClick={logout} disabled={pending}>Sign out</button>
              </div>
            </form>
          </>
        ) : (
          <>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-base-content/60">Private workspace</p>
              <h2 className="mt-2 text-2xl font-bold">Start with a secure account.</h2>
              <p className="mt-3 text-sm leading-6 text-base-content/65">Your learning data remains separate from AI generation. Mastery decisions will stay deterministic and auditable.</p>
            </div>
            {message && <div className="alert alert-error" role="alert">{message}</div>}
            {features?.dev_login && <button className="btn btn-neutral w-full" onClick={localLogin} disabled={pending}>Enter local workspace</button>}
            {features?.oidc_login && <a className="btn btn-neutral w-full" href="/api/v1/auth/login">Continue securely</a>}
            {!features?.dev_login && !features?.oidc_login && <div className="alert" role="status">Identity provider setup is pending for this environment.</div>}
          </>
        )}
      </div>
    </section>
  );
}
