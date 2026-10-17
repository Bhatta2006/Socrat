'use client';

import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Textarea } from '@/components/ui/textarea';

/** Opens the "Report a problem" dialog from anywhere (menu, error page, settings). */
export function openReportProblem() {
  window.dispatchEvent(new CustomEvent('socrat:report'));
}

const CATEGORIES = [
  ['bug', 'Something is broken'],
  ['content', 'A lesson, question or problem is wrong'],
  ['idea', 'An idea or request'],
  ['other', 'Something else'],
] as const;

/** Mounted once in the app shell. Sends the message and the page path, nothing else. */
export function ReportProblem() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [category, setCategory] = useState<(typeof CATEGORIES)[number][0]>('bug');
  const [sending, setSending] = useState(false);

  useEffect(() => {
    const show = () => setOpen(true);
    window.addEventListener('socrat:report', show);
    return () => window.removeEventListener('socrat:report', show);
  }, []);

  async function send() {
    setSending(true);
    try {
      await api.post('/problem-reports', { message: message.trim(), category, route: window.location.pathname.slice(0, 120) });
      toast.success('Thanks. We read every report.');
      setMessage('');
      setOpen(false);
    } catch (e) {
      toast.error(explain(e));
    } finally {
      setSending(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Report a problem</DialogTitle>
          <DialogDescription>Tell us what happened. We include the page you are on; nothing else from your screen.</DialogDescription>
        </DialogHeader>
        <label className="grid gap-1.5 text-sm font-medium">
          What is it about?
          <NativeSelect value={category} onChange={e => setCategory(e.target.value as typeof category)}>
            {CATEGORIES.map(([value, label]) => <NativeSelectOption key={value} value={value}>{label}</NativeSelectOption>)}
          </NativeSelect>
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          What happened?
          <Textarea rows={5} maxLength={2000} value={message} onChange={e => setMessage(e.target.value)} placeholder="What you did, what you expected, what you saw" />
        </label>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={send} disabled={sending || message.trim().length < 3}>{sending ? 'Sending' : 'Send report'}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
