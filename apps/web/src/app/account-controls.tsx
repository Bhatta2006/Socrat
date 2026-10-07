'use client';

import { FormEvent, useEffect, useRef, useState } from 'react';

type Preferences = { revision: number; reminders_consent: boolean; reminder_time: string; quiet_start: string; quiet_end: string; timezone: string; reduced_motion: boolean };
export type DeletionReceipt = { id: string; receipt_token: string; status: string; deadline_at: number; tasks: Record<string, string | { status: string }> };
function download(value: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }));
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ReceiptStatus({ initial }: { initial: DeletionReceipt }) {
  const [receipt, setReceipt] = useState(initial);
  const [message, setMessage] = useState('');
  const [pending, setPending] = useState(false);
  async function refresh() {
    setPending(true); setMessage('');
    try {
      const response = await fetch(`/api/v1/privacy/requests/${receipt.id}`, { headers: { 'X-Privacy-Token': receipt.receipt_token } });
      if (!response.ok) throw new Error();
      setReceipt({ ...await response.json(), receipt_token: receipt.receipt_token });
    } catch { setMessage('Cleanup status could not be loaded. Keep your receipt and try again.'); }
    finally { setPending(false); }
  }
  return <section className="card card-border" aria-label="Deletion receipt"><div className="card-body">
    <h2 className="card-title">Your deletion request</h2>
    <p>Your sessions have been revoked. Cleanup status: {receipt.status.replaceAll('_', ' ').replaceAll('pending', 'awaiting cleanup')}.</p>
    <p>Cleanup deadline: {new Date(receipt.deadline_at * 1000).toLocaleDateString()}.</p>
    <ul>{Object.entries(receipt.tasks).map(([name, task]) => <li key={name}>{name.replaceAll('_', ' ')}: {(typeof task === 'string' ? task : task.status).replaceAll('_', ' ').replaceAll('pending', 'awaiting cleanup')}</li>)}</ul>
    <p>Save this private receipt before closing the page. It contains the token needed to check cleanup after sign-out.</p>
    {message && <p role="alert">{message}</p>}
    <div className="card-actions"><button className="btn" disabled={pending} onClick={refresh}>Check cleanup status</button>
      <button className="btn" onClick={() => download(receipt, 'socrat-deletion-receipt.json')}>Save deletion receipt</button></div>
  </div></section>;
}

export function ReceiptImport({ onLoaded }: { onLoaded: (receipt: DeletionReceipt) => void }) {
  const [error, setError] = useState('');
  return <details><summary className="cursor-pointer py-3">Check a saved deletion receipt</summary>
    <label className="flex flex-col gap-2">Open your private receipt JSON file
      <input className="file-input w-full" type="file" accept="application/json,.json" onChange={async event => {
        setError(''); const file = event.target.files?.[0]; if (!file) return;
        try {
          if (file.size > 16384) throw new Error();
          const value = JSON.parse(await file.text());
          if (typeof value.id !== 'string' || !/^[a-f0-9-]{36}$/.test(value.id) || typeof value.receipt_token !== 'string' || value.receipt_token.length < 32) throw new Error();
          const response = await fetch(`/api/v1/privacy/requests/${value.id}`, { headers: { 'X-Privacy-Token': value.receipt_token } });
          if (!response.ok) throw new Error();
          onLoaded({ ...await response.json(), receipt_token: value.receipt_token });
        } catch { setError('This receipt could not be verified. Check the file and try again.'); }
      }} />
    </label>
    <p className="text-sm">The file is read on your device. Only its receipt ID and token are used to retrieve cleanup status.</p>
    {error && <p role="alert">{error}</p>}
  </details>;
}

export default function AccountControls({ csrfToken, remindersEnabled, onDeleted }: {
  csrfToken: string; remindersEnabled: boolean; onDeleted: (receipt: DeletionReceipt) => void;
}) {
  const [value, setValue] = useState<Preferences | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [confirmation, setConfirmation] = useState('');
  const [reminders, setReminders] = useState<{ id: string; message: string }[]>([]);
  const deletionKey = useRef<{ request_id: string; receipt_token: string } | null>(null);
  async function request(path: string, method = 'GET', body?: unknown) {
    const response = await fetch(path, { method, headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrfToken },
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}) });
    if (!response.ok) {
      const code = (await response.json()).error?.code;
      throw new Error(code === 'preferences_revision_stale' ? 'Preferences changed in another window. Reload before saving.' : 'Your request could not be saved. Please retry.');
    }
    return response.status === 204 ? null : response.json();
  }
  useEffect(() => {
    let active = true;
    fetch('/api/v1/preferences').then(async response => {
      if (!response.ok) throw new Error();
      const preferences = await response.json();
      if (active) { setValue(preferences); document.documentElement.dataset.reducedMotion = String(preferences.reduced_motion); }
    }).catch(() => { if (active) setError('Preferences could not be loaded. Reload to try again.'); });
    return () => { active = false; delete document.documentElement.dataset.reducedMotion; };
  }, []);
  useEffect(() => {
    if (!remindersEnabled || !value?.reminders_consent) { setReminders([]); return; }
    let active = true;
    const check = () => {
      if (document.visibilityState !== 'visible') return;
      fetch('/api/v1/reminders/check', { method: 'POST', headers: { 'X-CSRF-Token': csrfToken } })
        .then(async response => { if (response.ok && active) setReminders((await response.json()).items); })
        .catch(() => { /* Reminder failure does not interrupt a learning task. */ });
    };
    check(); const timer = setInterval(check, 60000);
    return () => { active = false; clearInterval(timer); };
  }, [value, csrfToken, remindersEnabled]);

  async function run(action: () => Promise<void>) {
    setPending(true); setError(''); setMessage('');
    try { await action(); } catch (err) { setError((err as Error).message); }
    finally { setPending(false); }
  }
  async function save(event: FormEvent) {
    event.preventDefault(); if (!value) return;
    await run(async () => {
      const { revision, ...preferences } = value;
      const saved = await request('/api/v1/preferences', 'PATCH', { ...preferences, expected_revision: revision });
      setValue(saved); document.documentElement.dataset.reducedMotion = String(saved.reduced_motion);
      setMessage('Accountability preferences saved.');
    });
  }
  return <section className="border-t border-base-300 pt-6 space-y-4" aria-label="Accountability and privacy" aria-busy={pending}>
    <h2 className="text-2xl font-bold">Accountability and privacy</h2>
    {reminders.map(item => <div className="alert" key={item.id}><p>{item.message}</p>
      <button className="btn" disabled={pending} onClick={() => run(async () => {
        await request(`/api/v1/reminders/${item.id}/opened`, 'POST'); setReminders(current => current.filter(row => row.id !== item.id));
      })}>Dismiss reminder</button></div>)}
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    {message && <p role="status">{message}</p>}
    {value && <form className="space-y-4" onSubmit={save}>
      <label className="flex items-center gap-3"><input type="checkbox" className="checkbox" checked={value.reminders_consent}
        onChange={event => setValue({ ...value, reminders_consent: event.target.checked })} />I consent to in-app reminders on planned study days.</label>
      <p className="text-sm">At most one reminder per local day, only in the hour after your chosen time. Paused plans and rest days stay quiet.</p>
      {!remindersEnabled && <p>Reminders are disabled in this environment. Your consent preference can still be saved.</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        {(['reminder_time', 'quiet_start', 'quiet_end'] as const).map(name => <label key={name} className="flex flex-col gap-2">{name.replaceAll('_', ' ')}
          <input className="input w-full" type="time" required value={value[name]} onChange={event => setValue({ ...value, [name]: event.target.value })} /></label>)}
        <label className="flex flex-col gap-2">Reminder timezone<input className="input w-full" required value={value.timezone} maxLength={64}
          onChange={event => setValue({ ...value, timezone: event.target.value })} /></label>
      </div>
      <p className="text-sm">Quiet hours can cross midnight. Matching start and end times means quiet all day. Learning schedules are managed in Schedule and recovery.</p>
      <label className="flex items-center gap-3"><input type="checkbox" className="checkbox" checked={value.reduced_motion}
        onChange={event => setValue({ ...value, reduced_motion: event.target.checked })} />Reduce interface motion</label>
      <button className="btn" type="submit" disabled={pending}>Save accountability preferences</button>
    </form>}
    <details><summary className="cursor-pointer py-3 font-semibold">Your data and privacy controls</summary>
      <div className="space-y-4 py-3">
        <p>We store identity and profile, learning evidence, code drafts and submissions, tutor exchanges and assessments. Model providers may process minimized learning context when model help is enabled. Separate consent is required to train a general model on your content.</p>
        <p>Raw code and tutor content have a 12-month default retention policy. Account deletion revokes sessions immediately and requests cleanup within 30 days, including backups and provider records. Shared editorial records need separate review. The deletion receipt shows what still needs cleanup.</p>
        <button className="btn" disabled={pending} onClick={() => run(async () => {
          download(await request('/api/v1/privacy/export', 'POST'), 'socrat-learning-data.json'); setMessage('Your learning data export is ready.');
        })}>Export my learning data</button>
        <p>Deleting your data removes your saved learning history and code. This cannot be undone.</p>
        <label className="flex flex-col gap-2">Type DELETE MY DATA to request deletion
          <input className="input w-full" value={confirmation} onChange={event => setConfirmation(event.target.value)} autoComplete="off" /></label>
        <button className="btn btn-error" disabled={pending || confirmation !== 'DELETE MY DATA'} onClick={() => run(async () => {
          if (!deletionKey.current) deletionKey.current = { request_id: crypto.randomUUID(),
            receipt_token: Array.from(crypto.getRandomValues(new Uint8Array(32)), byte => byte.toString(16).padStart(2, '0')).join('') };
          const receipt = await request('/api/v1/privacy/delete', 'POST', { confirmation, ...deletionKey.current }); onDeleted(receipt);
        })}>Request account deletion</button>
      </div>
    </details>
  </section>;
}
