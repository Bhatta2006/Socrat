'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLearner } from '../learner-context';
import { ReceiptImport, ReceiptStatus, type DeletionReceipt } from '../account-controls';

export default function Login() {
  const { features, refresh } = useLearner();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [receipt, setReceipt] = useState<DeletionReceipt | null>(null);
  async function signIn(persona: string) {
    setBusy(true); setError('');
    try {
      const response = await fetch(features?.demo_mode ? '/api/v1/demo/login' : '/api/v1/auth/dev-login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(features?.demo_mode ? { persona } : { subject: 'local-learner' }),
      });
      if (!response.ok) throw new Error();
      await refresh();
      router.push(persona === 'fresh' ? '/onboarding' : '/today');
    } catch { setError('Sign-in could not connect. Please try again.'); setBusy(false); }
  }
  return <section className="login-layout"><div><p className="eyebrow">A place to think clearly</p><h1 tabIndex={-1}>Make your next<br />practice count.</h1><p className="lede">A plan that fits your day. Help that makes you think. Evidence you can trust.</p></div>
    <div className="surface login-panel"><h2>Welcome to Socrat</h2><p>Choose where to begin.</p>{error && <p role="alert">{error}</p>}
      {features?.demo_mode ? <><div className="persona-list">{[['beginner', 'Beginner', 'Python · start from zero'], ['interview', 'Interview prep', 'Java · practise for interviews'], ['competitive', 'Competitive', 'C++ · timed practice and upsolve']].map(([key, title, detail]) => <button className="persona-button" disabled={busy} key={key} onClick={() => void signIn(key)}><strong>Continue as {title}</strong><span>{detail}</span></button>)}</div><button className="btn btn-primary w-full" disabled={busy} onClick={() => void signIn('fresh')}>Start fresh as a new learner</button></>
        : <>{features?.dev_login && <button className="btn btn-primary" disabled={busy} onClick={() => void signIn('local')}>Enter local workspace</button>}{features?.oidc_login && <a className="btn btn-primary" href="/api/v1/auth/login">Continue securely</a>}</>}
      <ReceiptImport onLoaded={setReceipt} />{receipt && <ReceiptStatus initial={receipt} />}
    </div></section>;
}
