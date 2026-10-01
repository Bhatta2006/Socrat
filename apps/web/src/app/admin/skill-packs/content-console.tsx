'use client';

import { useEffect, useState } from 'react';

type Profile = { id: string; csrf_token: string };
type Version = {
  id: string;
  key: string;
  version: string;
  status: string;
  is_active: boolean;
  digest: string;
};
type Manifest = {
  key: string;
  version: string;
  name: string;
  release_stage: string;
  concepts: Array<{ key: string }>;
  content: Array<{ key: string; kind: string }>;
};
type Review = { role: string; decision: string; note: string; reviewer_id: string };
type Inspection = {
  id: string;
  status: string;
  digest: string;
  manifest: Manifest;
  required_reviews: string[];
  reviews: Review[];
};
type Access = 'loading' | 'sign-in' | 'denied' | 'ready' | 'unavailable';

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { ...init, credentials: 'same-origin' });
  const value = await response.json().catch(() => null);
  if (!response.ok) {
    const code = value?.error?.code ?? `http_${response.status}`;
    const requestId = value?.error?.request_id;
    throw new Error(requestId ? `${code} (request ${requestId})` : code);
  }
  return value as T;
}

export default function ContentConsole() {
  const [access, setAccess] = useState<Access>('loading');
  const [profile, setProfile] = useState<Profile | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [versions, setVersions] = useState<Version[]>([]);
  const [selected, setSelected] = useState<Inspection | null>(null);
  const [manifestText, setManifestText] = useState('');
  const [reviewRole, setReviewRole] = useState('');
  const [reviewDecision, setReviewDecision] = useState('approve');
  const [reviewNote, setReviewNote] = useState('');
  const [quarantineReason, setQuarantineReason] = useState('');
  const [itemKey, setItemKey] = useState('');
  const [message, setMessage] = useState('');
  const [isError, setIsError] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const person = await api<Profile>('/api/v1/me');
        const own = await api<{ roles: string[] }>('/api/v1/admin/content-roles');
        if (!active) return;
        setProfile(person);
        setRoles(own.roles);
        if (own.roles.length === 0) {
          setAccess('denied');
          return;
        }
        const inventory = await api<Version[]>('/api/v1/admin/skill-packs');
        if (active) {
          setVersions(inventory);
          setAccess('ready');
        }
      } catch (error) {
        if (!active) return;
        setAccess((error as Error).message === 'authentication_required' ? 'sign-in' : 'unavailable');
      }
    }
    void load();
    return () => { active = false; };
  }, []);

  async function refresh(versionId?: string) {
    const inventory = await api<Version[]>('/api/v1/admin/skill-packs');
    setVersions(inventory);
    if (versionId) {
      const detail = await api<Inspection>(`/api/v1/admin/skill-packs/${encodeURIComponent(versionId)}`);
      setSelected(detail);
      setReviewRole('');
      setItemKey('');
    }
  }

  async function mutate(path: string, payload: unknown, success: string, versionId?: string): Promise<boolean> {
    if (!profile) return false;
    setBusy(true);
    setMessage('');
    try {
      await api(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile.csrf_token },
        body: payload === undefined ? undefined : JSON.stringify(payload),
      });
      await refresh(versionId);
      setIsError(false);
      setMessage(success);
      return true;
    } catch (error) {
      setIsError(true);
      setMessage(`Action failed: ${(error as Error).message}`);
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function importManifest() {
    let manifest: unknown;
    try {
      manifest = JSON.parse(manifestText);
    } catch {
      setIsError(true);
      setMessage('Manifest JSON is invalid. Correct the syntax and try again.');
      return;
    }
    if (!profile) return;
    setBusy(true);
    setMessage('');
    try {
      const imported = await api<{ id: string }>('/api/v1/admin/skill-packs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': profile.csrf_token },
        body: JSON.stringify(manifest),
      });
      await refresh(imported.id);
      setManifestText('');
      setIsError(false);
      setMessage('Manifest imported as a draft version.');
    } catch (error) {
      setIsError(true);
      setMessage(`Import failed: ${(error as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  const reviewableRoles = selected?.required_reviews.filter(role => roles.includes(role)
    && !selected.reviews.some(review => review.role === role && review.reviewer_id === profile?.id)) ?? [];
  const hasReleaseRole = roles.includes('release_owner');
  const approvals = new Set(selected?.reviews.filter(review => review.decision === 'approve').map(review => review.role));
  const rejected = selected?.reviews.some(review => review.decision === 'reject') ?? false;
  const canPublish = selected?.status === 'draft' && selected.manifest.release_stage === 'candidate'
    && selected.required_reviews.every(role => approvals.has(role)) && !rejected;

  return (
    <main className="min-h-screen bg-base-100 text-base-content">
      <div className="mx-auto max-w-7xl px-5 py-6 sm:px-8 sm:py-10">
        <header className="flex flex-col gap-3 border-b border-base-300 pb-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <a href="/" className="text-sm font-bold tracking-tight">SOCRAT</a>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">Skill-pack operations</h1>
          </div>
          <a className="btn" href="/">Back to workspace</a>
        </header>

        {access === 'loading' && <p className="mt-8" role="status">Checking content access…</p>}
        {access === 'sign-in' && <div className="alert mt-8" role="alert">Sign in from the workspace to access content operations.</div>}
        {access === 'denied' && <div className="alert mt-8" role="alert">Content role required</div>}
        {access === 'unavailable' && <div className="alert alert-error mt-8" role="alert">Content operations are temporarily unavailable.</div>}

        {access === 'ready' && (
          <>
            <p className="mt-6 text-sm text-base-content/70">Import, review, release, and quarantine versioned skill packs. The API enforces every role and publication gate.</p>
            <p className="mt-2 text-sm text-base-content/70">Your roles: {roles.join(', ')}</p>
            {message && <div className={`alert mt-6 ${isError ? 'alert-error' : 'alert-success'}`} role={isError ? 'alert' : 'status'}>{message}</div>}

            <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
              <div className="space-y-6">
                <section className="card card-border bg-base-100 shadow-none">
                  <div className="card-body">
                    <h2 className="card-title">Versions</h2>
                    {versions.length === 0 ? <p className="text-sm text-base-content/70">No versions imported yet.</p> : (
                      <ul className="list">
                        {versions.map(version => (
                          <li className="list-row items-center" key={version.id}>
                            <button className="btn btn-ghost list-col-grow justify-start" disabled={busy} onClick={() => { setMessage(''); void refresh(version.id); }}>
                              {version.key} {version.version}
                            </button>
                            <span className="badge badge-outline">{version.is_active ? 'active' : version.status}</span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                </section>

                {roles.includes('author') && <section className="card card-border bg-base-100 shadow-none">
                  <div className="card-body">
                    <h2 className="card-title">Import manifest</h2>
                    <p className="text-sm text-base-content/70">Paste a validated skill-pack JSON document. Import creates an immutable draft version.</p>
                    <fieldset className="fieldset">
                      <legend className="fieldset-legend">Manifest JSON</legend>
                      <textarea className="textarea h-48 w-full font-mono text-xs" aria-label="Manifest JSON" value={manifestText} onChange={event => setManifestText(event.target.value)} />
                    </fieldset>
                    <div className="card-actions"><button className="btn" disabled={busy || !manifestText.trim()} onClick={() => void importManifest()}>Import draft</button></div>
                  </div>
                </section>}
              </div>

              <section className="card card-border bg-base-100 shadow-none">
                <div className="card-body gap-6">
                  <h2 className="card-title">Version details</h2>
                  {!selected ? <p className="text-sm text-base-content/70">Select a version to inspect its manifest and release controls.</p> : (
                    <>
                      <div>
                        <h3 className="text-xl font-semibold">{selected.manifest.name}</h3>
                        <p className="mt-1 font-mono text-sm">{selected.manifest.key} · {selected.manifest.version}</p>
                        <p className="mt-2 text-xs text-base-content/60 break-all">SHA-256 {selected.digest}</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <span className="badge badge-outline">{selected.status}</span>
                          <span className="badge badge-outline">{selected.manifest.release_stage}</span>
                          <span className="badge badge-outline">{selected.manifest.concepts?.length ?? 0} concepts</span>
                          <span className="badge badge-outline">{selected.manifest.content?.length ?? 0} items</span>
                        </div>
                      </div>
                      {selected.status === 'draft' && <div className="alert" role="note">Draft versions are not available to learners.</div>}

                      <div>
                        <h3 className="font-semibold">Required reviews</h3>
                        <ul className="list mt-2">
                          {selected.required_reviews.map(role => {
                            const decisions = selected.reviews.filter(entry => entry.role === role);
                            const decision = decisions.some(entry => entry.decision === 'reject')
                              ? 'reject' : decisions.some(entry => entry.decision === 'approve') ? 'approve' : 'pending';
                            return <li className="list-row" key={role}>
                              <span className="list-col-grow">{role.replaceAll('_', ' ')}</span>
                              <span className="badge badge-outline">{decision}</span>
                              {decisions.map(entry => <small className="list-col-wrap text-base-content/70" key={`${entry.reviewer_id}-${entry.role}`}>{entry.note}</small>)}
                            </li>;
                          })}
                        </ul>
                      </div>

                      {selected.status === 'draft' && reviewableRoles.length > 0 && <div className="border-t border-base-300 pt-5">
                        <h3 className="font-semibold">Record review</h3>
                        <div className="mt-3 grid gap-3 sm:grid-cols-2">
                          <fieldset className="fieldset">
                            <legend className="fieldset-legend">Review role</legend>
                            <select className="select w-full" aria-label="Review role" value={reviewRole} onChange={event => setReviewRole(event.target.value)}>
                              <option value="">Choose role</option>
                              {reviewableRoles.map(role => <option key={role} value={role}>{role.replaceAll('_', ' ')}</option>)}
                            </select>
                          </fieldset>
                          <fieldset className="fieldset">
                            <legend className="fieldset-legend">Decision</legend>
                            <select className="select w-full" aria-label="Decision" value={reviewDecision} onChange={event => setReviewDecision(event.target.value)}>
                              <option value="approve">Approve</option>
                              <option value="reject">Reject</option>
                            </select>
                          </fieldset>
                        </div>
                        <fieldset className="fieldset mt-3">
                          <legend className="fieldset-legend">Review note</legend>
                          <textarea className="textarea w-full" aria-label="Review note" minLength={10} maxLength={1000} value={reviewNote} onChange={event => setReviewNote(event.target.value)} />
                        </fieldset>
                        <button className="btn mt-3" disabled={busy || !reviewRole || reviewNote.trim().length < 10} onClick={async () => {
                          if (await mutate(`/api/v1/admin/skill-packs/${selected.id}/reviews`, { role: reviewRole, decision: reviewDecision, note: reviewNote }, 'Review recorded.', selected.id)) setReviewNote('');
                        }}>Record review</button>
                      </div>}

                      {selected.status === 'draft' && hasReleaseRole && <div className="border-t border-base-300 pt-5">
                        <h3 className="font-semibold">Publication</h3>
                        <p className="mt-2 text-sm text-base-content/70">Requires a candidate manifest, every required approval, and a matching digest. Release evidence must be checked by the named reviewers.</p>
                        <button className="btn mt-3" disabled={busy || !canPublish} onClick={() => void mutate(`/api/v1/admin/skill-packs/${selected.id}/publish`, undefined, 'Version published.', selected.id)}>Publish version</button>
                      </div>}

                      {selected.status === 'released' && hasReleaseRole && <div className="border-t border-base-300 pt-5">
                        <h3 className="font-semibold">Quarantine</h3>
                        <fieldset className="fieldset mt-3">
                          <legend className="fieldset-legend">Quarantine reason</legend>
                          <textarea className="textarea w-full" aria-label="Quarantine reason" minLength={10} maxLength={500} value={quarantineReason} onChange={event => setQuarantineReason(event.target.value)} />
                        </fieldset>
                        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                          <button className="btn btn-error" disabled={busy || quarantineReason.trim().length < 10} onClick={() => {
                            if (window.confirm('Quarantine this released pack version?')) void mutate(`/api/v1/admin/skill-packs/${selected.id}/quarantine`, { reason: quarantineReason }, 'Pack quarantined.', selected.id);
                          }}>Quarantine pack</button>
                          {selected.manifest.content.length > 0 && <>
                            <select className="select" aria-label="Content item" value={itemKey} onChange={event => setItemKey(event.target.value)}>
                              <option value="">Choose item</option>
                              {selected.manifest.content.map(item => <option key={item.key} value={item.key}>{item.key}</option>)}
                            </select>
                            <button className="btn" disabled={busy || !itemKey || quarantineReason.trim().length < 10} onClick={() => {
                              if (window.confirm(`Quarantine item ${itemKey}?`)) void mutate(`/api/v1/admin/skill-packs/${selected.id}/items/${encodeURIComponent(itemKey)}/quarantine`, { reason: quarantineReason }, 'Item quarantined.', selected.id);
                            }}>Quarantine item</button>
                          </>}
                        </div>
                      </div>}

                      <details className="border-t border-base-300 pt-5">
                        <summary className="cursor-pointer font-semibold">Full manifest</summary>
                        <pre className="mt-3 max-h-96 overflow-auto rounded-box bg-base-200 p-4 text-xs">{JSON.stringify(selected.manifest, null, 2)}</pre>
                      </details>
                    </>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
