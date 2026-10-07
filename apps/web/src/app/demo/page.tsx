'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Screen, useLearner } from '../learner-context';
export default function Page() {
  const { profile, features, refresh } = useLearner(); const router = useRouter();
  const [days, setDays] = useState(7); const [clock, setClock] = useState<{ server_now: number; offset_days: number } | null>(null);
  const [message, setMessage] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { if (features?.demo_mode && profile) fetch('/api/v1/demo/clock').then(r => r.json()).then(setClock).catch(() => setMessage('The clock could not connect.')); }, [features, profile]);
  async function act(action: string) {
    setBusy(true); setMessage('');
    try { const response = await fetch('/api/v1/demo/controls', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile?.csrf_token ?? '' }, body: JSON.stringify({ action, days }) }); if (!response.ok) throw new Error(); const data = await response.json(); if (data.reset) { await refresh(); router.push('/onboarding'); } else { setClock(data); setMessage(data.message); } }
    catch { setMessage('The control could not be saved. Your learning evidence is preserved.'); } finally { setBusy(false); }
  }
  return <Screen title="Demo controls">{features?.demo_mode ? <div className="surface space-y-5"><p>This clock applies to all learners in this isolated demo database. It advances dates without inventing answers, scores, or mastery.</p>{clock && <p role="status">Demo date: {new Date(clock.server_now * 1000).toLocaleDateString('en-IN', { timeZone: profile?.timezone })} · {clock.offset_days} days ahead</p>}
    <label>Days to move forward<input className="input block" type="number" min={1} max={30} value={days} onChange={e => setDays(Number(e.target.value))} /></label>
    <div className="flex flex-wrap gap-3">{[['advance', 'Move clock forward'], ['missed_days', 'Simulate missed days'], ['weekly', 'Move to weekly check'], ['retention', 'Move to retention check'], ['reset', 'Reset this learner']].map(([action, title]) => <button className="btn" disabled={busy} key={action} onClick={() => void act(action)}>{title}</button>)}</div>
    {message && <p role="status">{message}</p>}<p>Complete a baseline before weekly checks. Retention requires independent evidence and the spaced-review policy. Recovery recalculates the schedule without adding a backlog.</p><div className="flex gap-3"><Link className="btn btn-primary" href="/today">View Today</Link><Link className="btn" href="/assessments">View assessments</Link><Link className="btn" href="/plan">Review recovery</Link></div>
  </div> : <p>Demo controls are only enabled for a development demo build.</p>}</Screen>;
}
