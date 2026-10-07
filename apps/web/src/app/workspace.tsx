'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { useLearner } from './learner-context';

export default function ProfileSettings() {
  const { profile, refresh } = useLearner();
  const [displayName, setDisplayName] = useState('');
  const [timezone, setTimezone] = useState('Asia/Kolkata');
  const [adult, setAdult] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  useEffect(() => { if (profile) { setDisplayName(profile.display_name); setTimezone(profile.timezone); setAdult(profile.adult_confirmed); } }, [profile]);
  async function save(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(''); setMessage('');
    try {
      new Intl.DateTimeFormat('en', { timeZone: timezone }).format();
      const response = await fetch('/api/v1/me', { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile?.csrf_token ?? '' }, body: JSON.stringify({ display_name: displayName, timezone, adult_confirmed: adult }) });
      if (!response.ok) throw new Error();
      await refresh(); setMessage('Profile saved.');
    } catch { setError('Review your name and IANA timezone, such as Asia/Kolkata, then try again.'); }
    finally { setBusy(false); }
  }
  return <form onSubmit={save} className="surface profile-form" aria-busy={busy}><h2>Your profile</h2><p>Set the name and local schedule you want to use.</p>
    <label>Display name<input className="input w-full" aria-label="Display name" value={displayName} onChange={e => setDisplayName(e.target.value)} maxLength={80} required /></label>
    <label>Timezone<input className="input w-full" aria-label="Timezone" value={timezone} onChange={e => setTimezone(e.target.value)} maxLength={64} required /></label>
    <label className="flex items-center gap-3"><input className="checkbox" type="checkbox" checked={adult} onChange={e => setAdult(e.target.checked)} />I confirm I am 18 or older.</label>
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
    <button className="btn btn-primary" disabled={busy || !displayName.trim()}>Save profile</button></form>;
}
