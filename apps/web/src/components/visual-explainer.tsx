'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { ChevronLeft, ChevronRight, Expand, Pause, Play, RotateCcw, ShieldCheck } from 'lucide-react';
import type { VisualArtifact, VisualState } from '@/lib/explainer';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Checkbox } from '@/components/ui/checkbox';
import './visual-explainer.css';

export default function VisualExplainer({ artifact }: { artifact: VisualArtifact }) {
  const { resolvedTheme } = useTheme();
  const frameSource = useMemo(() => { const url = new URL(artifact.frame_url); url.searchParams.set('theme', resolvedTheme === 'dark' ? 'dark' : 'light'); return url.toString(); }, [artifact.frame_url, resolvedTheme]);
  const frame = useRef<HTMLIFrameElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const heartbeat = useRef(Date.now());
  const latest = useRef<VisualState>({ count: artifact.qa.step_count, current: 0, description: '', height: 650 });
  const [state, setState] = useState(latest.current);
  const [ready, setReady] = useState(false);
  const [failure, setFailure] = useState('');
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState('1');
  const [reduced, setReduced] = useState(false);
  const [full, setFull] = useState(false);
  const send = useCallback((data: Record<string, unknown>) => {
    frame.current?.contentWindow?.postMessage({ ...data, channel: artifact.id }, '*');
  }, [artifact.id]);
  const theme = useCallback(() => {
    const styles = getComputedStyle(document.documentElement);
    const names = ['background','foreground','card','muted','muted-foreground','border','primary','primary-foreground','success','warning','destructive','chart-1','chart-2','chart-3','chart-4','chart-5','radius'];
    send({ type: 'theme', tokens: Object.fromEntries(names.map(name => [name, styles.getPropertyValue('--' + name).trim()])), dark: resolvedTheme === 'dark', reducedMotion: reduced });
  }, [send, resolvedTheme, reduced]);

  useEffect(() => {
    const preference = matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(preference.matches);
    const update = () => { setReduced(preference.matches); if (preference.matches) setPlaying(false); };
    preference.addEventListener('change', update);
    return () => preference.removeEventListener('change', update);
  }, []);
  useEffect(() => {
    function message(event: MessageEvent) {
      if (event.origin !== 'null' || event.source !== frame.current?.contentWindow || event.data?.channel !== artifact.id) return;
      const data = event.data;
      if (data.type === 'ready') { heartbeat.current = Date.now(); setReady(true); }
      else if (data.type === 'heartbeat') heartbeat.current = Date.now();
      else if (data.type === 'error') { setFailure('This visual stopped responding. Regenerate it or report the issue.'); setPlaying(false); }
      else if (data.type === 'state' && Number.isInteger(data.count) && data.count >= 1 && data.count <= 2000 && Number.isInteger(data.current) && data.current >= 0 && data.current < data.count && typeof data.description === 'string' && data.description.length <= 6000 && Number.isFinite(data.height)) {
        setReady(true);
        const next = { count: data.count, current: data.current, description: data.description, height: Math.min(1600, Math.max(420, data.height)) };
        latest.current = next;
        setState(previous => previous.count === next.count && previous.current === next.current && previous.description === next.description && previous.height === next.height ? previous : next);
      }
    }
    addEventListener('message', message);
    const watchdog = setInterval(() => {
      if (document.hidden) { heartbeat.current = Date.now(); return; }
      if (Date.now() - heartbeat.current > 8000) { setFailure('The visual did not respond in time. Regenerate it or report the issue.'); setPlaying(false); }
    }, 1000);
    return () => { removeEventListener('message', message); clearInterval(watchdog); };
  }, [artifact.id]);
  useEffect(() => { if (ready) theme(); }, [ready, theme]);
  useEffect(() => { setReady(false);setPlaying(false);heartbeat.current=Date.now(); }, [frameSource]);
  useEffect(() => {
    if (!playing || reduced || !ready || failure) return;
    const timer = setInterval(() => {
      const current = latest.current;
      if (current.current >= current.count - 1) { setPlaying(false); return; }
      send({ type: 'step', index: current.current + 1 });
    }, 1400 / Number(speed));
    return () => clearInterval(timer);
  }, [playing, reduced, ready, failure, send, speed]);
  useEffect(() => { const update = () => setFull(document.fullscreenElement === canvas.current); document.addEventListener('fullscreenchange', update); return () => document.removeEventListener('fullscreenchange', update); }, []);
  function seek(index: number) { setPlaying(false); send({ type: 'step', index }); }

  return <Card className="overflow-hidden">
    <div ref={canvas} className="visual-canvas relative bg-background">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-2 text-sm"><ShieldCheck className="size-4 text-primary" /><span>Interactive canvas</span><span className="text-xs text-muted-foreground">Isolated preview</span></div>
        <Button variant="ghost" className="min-h-11" onClick={async () => { if (full) await document.exitFullscreen(); else await canvas.current?.requestFullscreen(); }} aria-label={full ? 'Exit expanded canvas' : 'Expand canvas'}><Expand className="size-4" /><span className="hidden sm:inline">{full ? 'Exit expanded view' : 'Expand'}</span></Button>
      </div>
      {failure ? <div role="alert" className="grid min-h-80 place-items-center p-8 text-center text-sm text-destructive">{failure}</div> : <>
        {!ready ? <p role="status" className="absolute inset-x-0 top-20 z-10 text-center text-sm text-muted-foreground">Opening your interactive visual…</p> : null}
        <iframe ref={frame} src={frameSource} title={artifact.title + ' — interactive visual'} sandbox="allow-scripts" referrerPolicy="no-referrer" allow="camera 'none'; microphone 'none'; geolocation 'none'; clipboard-read 'none'; clipboard-write 'none'" className="block w-full border-0" style={{ height: state.height, opacity: ready ? 1 : 0 }} />
      </>}
      <div className="border-t bg-card p-4" onKeyDown={event => {
        if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || !ready || failure) return;
        if (event.key === 'ArrowRight') { event.preventDefault(); seek(Math.min(state.count - 1, state.current + 1)); }
        if (event.key === 'ArrowLeft') { event.preventDefault(); seek(Math.max(0, state.current - 1)); }
      }}>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="outline" className="min-h-11" disabled={!ready || !!failure || state.current === 0} onClick={() => seek(state.current - 1)} aria-label="Previous visual step"><ChevronLeft /></Button>
          <Button className="min-h-11 min-w-24" disabled={!ready || !!failure || reduced || state.count <= 1} onClick={() => { if (state.current === state.count - 1) seek(0); setPlaying(value => !value); }}>{playing ? <Pause /> : <Play />}{playing ? 'Pause' : 'Play'}</Button>
          <Button variant="outline" className="min-h-11" disabled={!ready || !!failure || state.current >= state.count - 1} onClick={() => seek(state.current + 1)} aria-label="Next visual step"><ChevronRight /></Button>
          <Button variant="ghost" className="min-h-11" disabled={!ready || !!failure} onClick={() => { setPlaying(false); send({ type: 'reset' }); }}><RotateCcw />Reset</Button>
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">{state.count > 1 ? `Step ${state.current + 1} / ${state.count}` : 'Live experiment'}</span>
          <label className="sr-only" htmlFor={`speed-${artifact.id}`}>Playback speed</label><NativeSelect id={`speed-${artifact.id}`} value={speed} className="min-h-11" onChange={event => setSpeed(event.target.value)}><NativeSelectOption value="0.5">0.5×</NativeSelectOption><NativeSelectOption value="1">1×</NativeSelectOption><NativeSelectOption value="2">2×</NativeSelectOption></NativeSelect>
        </div>
        {state.count > 1 ? <div className="mt-4"><label htmlFor={`timeline-${artifact.id}`} className="sr-only">Visual timeline</label><input id={`timeline-${artifact.id}`} type="range" min={0} max={state.count - 1} value={state.current} disabled={!ready || !!failure} onChange={event => seek(Number(event.target.value))} className="visual-timeline" /></div> : null}
        <div className="mt-4 flex items-center gap-2"><Checkbox id={`motion-${artifact.id}`} checked={reduced} onCheckedChange={value => { setReduced(value === true); if (value) setPlaying(false); }} /><label htmlFor={`motion-${artifact.id}`} className="text-xs text-muted-foreground">Reduce motion · step manually</label></div>
        <p role="status" className="mt-4 min-h-6 text-sm leading-relaxed">{state.description}</p>
      </div>
    </div>
    <CardContent className="pt-0 text-xs text-muted-foreground">AI-generated visual. Browser checks{artifact.qa.ai_review === 'passed' ? ' and AI review' : ''} passed; factual accuracy has not been verified.</CardContent>
  </Card>;
}
