'use client';

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export type Profile = { id: string; display_name: string; timezone: string; adult_confirmed: boolean; csrf_token: string };
export type Features = { demo_mode: boolean; execution_backend: string; dev_login: boolean; oidc_login: boolean; diagnostics: boolean; reminders: boolean; [key: string]: boolean | string };
export type Goal = { id: string; normalized_statement: string; routing_outcome: string; active_track: string; goal: { language: string; goal_template_id: string } };
type Learner = { profile: Profile | null; features: Features | null; goal: Goal | null; loading: boolean; error: string; refresh: () => Promise<void> };
const Context = createContext<Learner | null>(null);
export function useLearner() { const value = useContext(Context); if (!value) throw new Error('Learner provider required'); return value; }

export function LearnerProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [features, setFeatures] = useState<Features | null>(null);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    setError('');
    try {
      const [flags, identity] = await Promise.all([fetch('/api/v1/features'), fetch('/api/v1/auth/status')]);
      if (!flags.ok || !identity.ok) throw new Error();
      setFeatures(await flags.json());
      const value = (await identity.json()).profile as Profile | null;
      setProfile(value);
      if (value) {
        const goals = await fetch('/api/v1/onboarding/goals');
        if (goals.ok) setGoal((await goals.json()).items[0] ?? null);
      } else setGoal(null);
    } catch { setError('The workspace could not connect. Your saved work is preserved and mastery has not changed.'); }
    finally { setLoading(false); }
  }, []);
  const pathname = usePathname();
  useEffect(() => { void refresh(); }, [refresh, pathname]);
  return <Context.Provider value={{ profile, features, goal, loading, error, refresh }}>{children}</Context.Provider>;
}

export function Screen({ title, children, requireGoal = false }: { title: string; children: React.ReactNode; requireGoal?: boolean }) {
  const { loading, profile, goal, error, refresh } = useLearner();
  return <section className="screen"><h1 tabIndex={-1} className="screen-title">{title}</h1>
    {error ? <div role="alert" className="alert alert-error"><p>{error}</p><button className="btn" onClick={() => void refresh()}>Try again</button></div>
      : loading ? <p role="status">Loading your workspace…</p>
      : !profile ? <p>Sign in to continue your saved learning. <Link className="btn btn-primary" href="/login">Sign in</Link></p>
      : requireGoal && !goal ? <p>Choose a goal to build your learning path. <Link className="btn btn-primary" href="/onboarding">Choose a goal</Link></p>
      : children}
  </section>;
}
