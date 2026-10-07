'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { LearnerProvider, useLearner } from './learner-context';

const nav = [['/today', 'Today'], ['/plan', 'Plan'], ['/progress', 'Progress'], ['/assessments', 'Assessments'], ['/settings', 'Settings']];
function Shell({ children }: { children: React.ReactNode }) {
  const { profile, features, refresh } = useLearner();
  const pathname = usePathname();
  const router = useRouter();
  const [dark, setDark] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => { const value = localStorage.getItem('socrat-theme') === 'dark'; setDark(value); document.documentElement.dataset.theme = value ? 'socrat-dark' : 'socrat'; }, []);
  useEffect(() => { document.querySelector<HTMLElement>('main h1')?.focus({ preventScroll: true }); }, [pathname]);
  async function logout() {
    const response = await fetch('/api/v1/auth/logout', { method: 'POST', headers: { 'X-CSRF-Token': profile?.csrf_token ?? '' } });
    if (!response.ok) { setMessage('Sign-out could not be saved. Please retry.'); return; }
    await refresh(); router.push('/login');
  }
  return <>
    <a className="skip-link" href="#main-content">Skip to main content</a>
    {features?.demo_mode && <div className="demo-banner">Demo build — sample content, local sandbox. Not reviewed for release.</div>}
    <header className="app-header"><Link className="wordmark" href="/">SOCRAT<span className="wordmark-dot" /></Link>
      <div className="header-tools"><button className="btn btn-ghost btn-sm" aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'} onClick={() => { const value = !dark; setDark(value); document.documentElement.dataset.theme = value ? 'socrat-dark' : 'socrat'; localStorage.setItem('socrat-theme', value ? 'dark' : 'light'); }}>{dark ? 'Light mode' : 'Dark mode'}</button>
        {profile ? <details className="user-menu"><summary>{profile.display_name || 'Your account'}</summary><div><Link href="/settings">Account settings</Link><button onClick={logout}>Sign out</button></div></details> : <Link className="btn btn-sm" href="/login">Sign in</Link>}
      </div></header>
    <div className={`app-frame ${pathname === '/' || pathname === '/login' ? 'public-frame' : ''}`}>
      {pathname !== '/' && pathname !== '/login' && <aside className="app-sidebar"><p className="eyebrow">Your workspace</p><nav aria-label="Main navigation">{nav.map(([href, label]) => <Link key={href} href={href} aria-current={pathname === href ? 'page' : undefined}>{label}</Link>)}{features?.demo_mode && <Link href="/demo" aria-current={pathname === '/demo' ? 'page' : undefined}>Demo controls</Link>}</nav><p className="sidebar-note">Build capability.<br />Prove it independently.</p></aside>}
      <main id="main-content" className="app-main">{message && <p role="alert">{message}</p>}
        {pathname !== '/' && pathname !== '/login' && <nav aria-label="Breadcrumb" className="breadcrumbs"><Link href="/today">Workspace</Link><span aria-hidden="true">/</span><span>{pathname.split('/')[1].replaceAll('-', ' ')}</span></nav>}
        {children}</main>
    </div><footer className="app-footer">Independent evidence. Thoughtful practice. Room to begin again.</footer>
  </>;
}
export default function AppShell({ children }: { children: React.ReactNode }) { return <LearnerProvider><Shell>{children}</Shell></LearnerProvider>; }
