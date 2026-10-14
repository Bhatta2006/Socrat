'use client';

import Link from 'next/link';
import dynamic from 'next/dynamic';
import { useEffect, useRef, useState } from 'react';
import { ArrowRight, CheckCircle2, ChevronDown, Flag, History, Lightbulb, LoaderCircle, Sparkles } from 'lucide-react';
import { ApiError, api, explain, stream } from '@/lib/api';
import { useGuard } from '@/lib/session';
import type { VisualArtifact } from '@/lib/explainer';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const VisualExplainer = dynamic(() => import('@/components/visual-explainer'), { ssr: false });
type Level = VisualArtifact['level'];
interface Suggestion { id: string; title: string; reason: string }
interface Saved { id: string; title: string; created_at: number }

const phases: Record<string, string> = {
  generating: 'Creating the visual, explanation and interactive controls…',
  checking: 'Checking that your visual opens and its controls work…',
  reviewing: 'Reviewing the explanation and visual for consistency with your question…',
  repairing: 'Fixing an issue before opening your visual…',
};

export default function PlaygroundPage() {
  const allowed = useGuard('active');
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [saved, setSaved] = useState<Saved[]>([]);
  const [prompt, setPrompt] = useState('');
  const [level, setLevel] = useState<Level>('standard');
  const [artifact, setArtifact] = useState<VisualArtifact | null>(null);
  const [previewVersion, setPreviewVersion] = useState(0);
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState('generating');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [reportOpen, setReportOpen] = useState(false);
  const [reason, setReason] = useState('');
  const [reporting, setReporting] = useState(false);
  const resultHeading = useRef<HTMLHeadingElement>(null);
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    if (!allowed) return;
    let active = true;
    Promise.all([api.get<{ suggestions: Suggestion[] }>('/playground'), api.get<{ items: Saved[] }>('/playground/artifacts')]).then(([overview, history]) => {
      if (active) { setSuggestions(overview.suggestions); setSaved(history.items); }
    }).catch(e => { if (active) setError(explain(e)); });
    return () => { active = false; };
  }, [allowed]);
  useEffect(() => {
    if (artifact) { resultHeading.current?.focus({ preventScroll: true }); resultHeading.current?.scrollIntoView({ block: 'start' }); }
  }, [artifact]);

  async function generate(request = prompt, depth = level) {
    setBusy(true); setArtifact(null); setError(''); setNotice(''); setPhase('generating');
    setPrompt(request); setLevel(depth);
    try {
      let complete = false;
      for await (const event of stream('/playground/generate', { prompt: request.trim(), level: depth, request_id: crypto.randomUUID() })) {
        if (event.event === 'progress') setPhase(String(event.data.phase));
        else if (event.event === 'error') throw new ApiError(502, String(event.data.code));
        else if (event.event === 'ready') {
          const result = event.data.artifact as unknown as VisualArtifact;
          setArtifact(result);
          setSaved(rows => [{ id: result.id, title: result.title, created_at: result.created_at }, ...rows.filter(row => row.id !== result.id)].slice(0,20));
          complete = true;
        }
      }
      if (!complete) throw new Error('Generation ended before the visual was ready');
    } catch (e) { setError(explain(e)); }
    finally { setBusy(false); }
  }
  async function openSaved(id: string) {
    setError(''); setNotice('');
    try { const result = await api.get<VisualArtifact>(`/playground/artifacts/${id}`); setPreviewVersion(value => value + 1); setArtifact(result); setPrompt(result.request); setLevel(result.level); }
    catch (e) { setError(explain(e)); }
  }
  async function report() {
    if (!artifact) return;
    setReporting(true);
    try {
      await api.post(`/playground/artifacts/${artifact.id}/report`, { reason: reason.trim() });
      setSaved(rows => rows.filter(row => row.id !== artifact.id)); setArtifact(null); setReportOpen(false); setReason('');
      setNotice('Reported. This visual has been removed from your saved explorations.');
    } catch (e) { setError(explain(e)); }
    finally { setReporting(false); }
  }
  if (!allowed || (!suggestions && !error)) return <Loading />;
  return <Page>
    <PageHeader eyebrow="Learn through exploration" title="Visual playground" description="Ask a question. Get an interactive visual built around the way you want to understand it." actions={<Button asChild variant="outline"><Link href="/plan">Your roadmap<ArrowRight /></Link></Button>} />
    <Card className="mb-6 border-primary/20">
      <CardHeader><CardTitle as="h2" className="flex items-center gap-2 text-base"><Sparkles className="size-4 text-primary" />What would you like to understand?</CardTitle><CardDescription>A concept, a comparison, a confusing step—tell the AI what to show and what you want to experiment with.</CardDescription></CardHeader>
      <CardContent className="grid gap-4">
        <label htmlFor="visual-request" className="sr-only">Your request</label>
        <Textarea ref={input} id="visual-request" value={prompt} disabled={busy} maxLength={4000} rows={4} className="min-h-28" placeholder="Describe what you want explained. Add your own example or ask for sliders, a simulation, a walkthrough…" onChange={event => setPrompt(event.target.value)} onKeyDown={event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && prompt.trim().length >= 5 && !busy) { event.preventDefault(); void generate(); } }} />
        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="visual-depth" className="text-sm text-muted-foreground">Explanation depth</label><NativeSelect id="visual-depth" value={level} disabled={busy} onChange={event => setLevel(event.target.value as Level)} className="min-h-11"><NativeSelectOption value="simple">Simple</NativeSelectOption><NativeSelectOption value="standard">Standard</NativeSelectOption><NativeSelectOption value="deep">Go deep</NativeSelectOption></NativeSelect>
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">{prompt.length}/4000</span>
          <Button disabled={busy || prompt.trim().length < 5} className="min-h-11 min-w-40" onClick={() => void generate()}>{busy ? <LoaderCircle className="animate-spin motion-reduce:animate-none" /> : <Sparkles />}{busy ? 'Creating your visual…' : 'Generate visual'}</Button>
        </div>
        {!!suggestions?.length && <div className="flex flex-wrap items-center gap-2 border-t pt-4"><span className="mr-1 flex items-center gap-1.5 text-xs text-muted-foreground"><Lightbulb className="size-3.5" />From your learning</span>{suggestions.map(item => <Button key={item.id} variant="outline" className="min-h-11" disabled={busy} title={item.reason} onClick={() => void generate(`Explain ${item.title} visually. Help me understand how it works with an interactive example.`)}>{item.title}<ArrowRight className="size-3" /></Button>)}</div>}
      </CardContent>
    </Card>
    {error ? <ErrorNote message={error} /> : null}
    {notice ? <p role="status" className="my-4 flex items-center gap-2 text-sm text-success"><CheckCircle2 className="size-4" />{notice}</p> : null}
    {busy ? <Card className="mb-6"><CardContent className="grid min-h-96 place-items-center py-12 text-center"><div><span className="mx-auto mb-6 grid size-16 place-items-center rounded-2xl bg-primary/10"><Sparkles className="size-7 text-primary" /></span><h2 className="text-xl font-semibold">A visual made for your question.</h2><p role="status" aria-live="polite" className="mt-3 max-w-md text-sm text-muted-foreground">{phases[phase] || phases.generating}</p><p className="mt-6 text-xs text-muted-foreground">The finished visual will open right here. Complex requests can take a little longer.</p></div></CardContent></Card> : artifact ? <section aria-label="Your generated visual" className="grid gap-5">
      <div className="flex flex-wrap items-start justify-between gap-4"><div className="min-w-0"><Badge variant="secondary" className="mb-3">AI-generated · interactive</Badge><h2 ref={resultHeading} tabIndex={-1} className="scroll-mt-20 text-2xl font-semibold tracking-tight outline-none">{artifact.title}</h2><p className="mt-2 max-w-3xl whitespace-pre-wrap text-sm leading-relaxed text-muted-foreground">You asked: {artifact.request}</p></div><div className="flex flex-wrap gap-2"><Button variant="outline" className="min-h-11" onClick={() => void generate(artifact.request, 'simple')}>Simpler</Button><Button variant="outline" className="min-h-11" onClick={() => void generate(artifact.request, 'deep')}>Go deeper</Button><Button variant="ghost" className="min-h-11" onClick={() => { setReportOpen(true); setReason(''); }}><Flag className="size-4" />Report an issue</Button></div></div>
      <VisualExplainer key={`${artifact.id}:${previewVersion}`} artifact={artifact} />
      <Card><Collapsible><CardHeader><CollapsibleTrigger asChild><Button variant="ghost" className="group min-h-11 w-full justify-between px-0 text-base font-semibold">Read the explanation<ChevronDown className="size-4 group-data-[state=open]:rotate-180" /></Button></CollapsibleTrigger></CardHeader><CollapsibleContent><CardContent><p className="whitespace-pre-wrap text-sm leading-7">{artifact.transcript}</p></CardContent></CollapsibleContent></Collapsible></Card>
    </section> : !busy ? <Card className="relative overflow-hidden border-0 bg-gradient-to-br from-primary/10 via-card to-card"><CardContent className="grid min-h-72 place-items-center py-12 text-center"><div className="max-w-lg"><span className="mx-auto mb-5 grid size-14 place-items-center rounded-2xl bg-primary/10"><Lightbulb className="size-6 text-primary" /></span><h2 className="text-2xl font-semibold tracking-tight">Make the idea something you can explore.</h2><p className="mt-3 text-sm leading-7 text-muted-foreground">Your question becomes a visual you can interact with: change inputs, move through an explanation, and see what happens. Every exploration is generated for your request.</p><Button variant="link" className="mt-3 min-h-11" onClick={() => input.current?.focus()}>Start with your question<ArrowRight /></Button></div></CardContent></Card> : null}
    {!!saved.length && <Card className="mt-6"><Collapsible><CardHeader><CollapsibleTrigger asChild><Button variant="ghost" className="group min-h-11 w-full justify-between px-0"><span className="flex items-center gap-2"><History className="size-4" />Your saved visuals <span className="text-muted-foreground">({saved.length})</span></span><ChevronDown className="size-4 group-data-[state=open]:rotate-180" /></Button></CollapsibleTrigger></CardHeader><CollapsibleContent><CardContent><ul className="grid max-h-80 gap-2 overflow-y-auto sm:grid-cols-2">{saved.map(item => <li key={item.id}><Button variant="outline" disabled={busy} className="h-auto min-h-14 w-full justify-between whitespace-normal text-left" onClick={() => void openSaved(item.id)}>{item.title}<ArrowRight className="size-4 shrink-0" /></Button></li>)}</ul></CardContent></CollapsibleContent></Collapsible></Card>}
    <Dialog open={reportOpen} onOpenChange={setReportOpen}><DialogContent><DialogHeader><DialogTitle>Report this visual</DialogTitle><DialogDescription>Tell us what was incorrect or did not work. Reporting removes this visual from your saved explorations.</DialogDescription></DialogHeader><label htmlFor="visual-report" className="text-sm font-medium">What went wrong?</label><Textarea id="visual-report" value={reason} onChange={event => setReason(event.target.value)} maxLength={1000} rows={4} /><DialogFooter><Button variant="outline" className="min-h-11" onClick={() => setReportOpen(false)}>Cancel</Button><Button className="min-h-11" disabled={reporting || reason.trim().length < 5} onClick={() => void report()}>{reporting ? 'Reporting…' : 'Send report'}</Button></DialogFooter></DialogContent></Dialog>
  </Page>;
}
