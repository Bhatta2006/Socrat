'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { CheckCircle2, Download, LogOut, Monitor, Moon, Sun, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { LANGUAGE_LABEL, hours } from '@/lib/routes';
import type { Course, Language, Profile } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading, Page, PageHeader } from '@/components/common';
import { Pill } from '@/components/choice';
import CodeforcesLink from '@/components/codeforces-link';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Spinner } from '@/components/ui/spinner';

const MINUTES = [15, 20, 30, 45, 60, 90, 120];
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const THEMES = [
  { id: 'light', label: 'Light', icon: Sun },
  { id: 'dark', label: 'Dark', icon: Moon },
  { id: 'system', label: 'System', icon: Monitor },
] as const;

function Appearance() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
        <CardDescription>Choose how Socrat looks. System follows your device.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid max-w-md grid-cols-3 gap-2" role="radiogroup" aria-label="Theme">
          {THEMES.map(t => {
            const active = mounted && (theme ?? 'system') === t.id;
            return (
              <button
                key={t.id}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => setTheme(t.id)}
                className={cn('grid justify-items-center gap-2 rounded-xl border p-4 text-sm font-medium transition-all hover:border-primary/50', active && 'border-primary bg-primary/5 ring-1 ring-primary')}
              >
                <t.icon className={cn('size-5', active ? 'text-primary' : 'text-muted-foreground')} />
                {t.label}
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function Settings() {
  const allowed = useGuard('enrolled');
  const { profile, refresh, signOut } = useSession();
  const router = useRouter();
  const [course, setCourse] = useState<Course | null>(null);
  const [name, setName] = useState('');
  const [language, setLanguage] = useState<Language>('python');
  const [minutes, setMinutes] = useState(30);
  const [weekdays, setWeekdays] = useState<number[]>([]);
  const [targetDate, setTargetDate] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState('');

  useEffect(() => {
    if (!profile?.enrollment) return;
    const e = profile.enrollment;
    setName(profile.display_name ?? '');
    setLanguage(e.language);
    setMinutes(e.minutes_per_day);
    setWeekdays(e.weekdays);
    setTargetDate(String(e.goal.target_date ?? ''));
    api.get<{ items: Course[] }>('/courses').then(r => setCourse(r.items.find(c => c.id === e.course) ?? null)).catch(() => undefined);
  }, [profile]);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    setStatus('');
    try {
      if (name.trim() && name.trim() !== profile?.display_name) await api.patch('/me', { display_name: name.trim() });
      await api.patch<Profile>('/enrollments/current', {
        language,
        minutes_per_day: minutes,
        weekdays,
        ...(targetDate ? { target_date: targetDate } : { clear_target_date: true }),
      });
      await refresh();
      setStatus('Saved. Your plan has been updated.');
      toast.success('Settings saved', { description: 'Your plan has been re-flowed around the new schedule.' });
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  async function exportData() {
    try {
      const data = await api.get<unknown>('/me/export');
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = `socrat-export-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      toast.success('Export downloaded');
    } catch (e) {
      setError(explain(e));
    }
  }

  async function deleteAccount() {
    setBusy(true);
    try {
      await api.del('/me');
      await signOut().catch(() => undefined);
      await refresh();
      router.replace('/');
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  if (!allowed || !profile?.enrollment) return <Loading />;
  const toggleDay = (i: number) => setWeekdays(w => (w.includes(i) ? (w.length > 1 ? w.filter(x => x !== i) : w) : [...w, i].sort()));

  return (
    <Page narrow>
      <PageHeader eyebrow="Settings" title="Your account and plan" description="Changes to your schedule re-flow your plan immediately." />

      <form onSubmit={save}>
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Profile and schedule</CardTitle>
            <CardDescription>How Socrat addresses you and how much time you have.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-6">
            <div className="grid gap-6 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="settings-name">Name</FieldLabel>
                <Input id="settings-name" className="h-9" value={name} onChange={e => setName(e.target.value)} maxLength={80} />
              </Field>
              <Field>
                <FieldLabel htmlFor="settings-language">Language</FieldLabel>
                <NativeSelect id="settings-language" className="w-full [&_select]:h-9" value={language} onChange={e => setLanguage(e.target.value as Language)}>
                  {(course?.languages ?? [language]).map(l => <NativeSelectOption key={l} value={l}>{LANGUAGE_LABEL[l]}</NativeSelectOption>)}
                </NativeSelect>
              </Field>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 px-4 py-3">
              <div>
                <p className="text-xs text-muted-foreground">Course</p>
                <p className="text-sm font-medium">{course?.title ?? profile.enrollment.course}</p>
              </div>
              <Button asChild variant="outline" size="sm"><Link href="/start">Switch course</Link></Button>
            </div>
            <fieldset>
              <legend className="mb-2 text-sm font-medium">Time per study day</legend>
              <div className="flex flex-wrap gap-2">
                {MINUTES.map(m => <Pill key={m} pressed={minutes === m} onClick={() => setMinutes(m)}>{hours(m)}</Pill>)}
              </div>
            </fieldset>
            <fieldset>
              <legend className="mb-2 text-sm font-medium">Study days</legend>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d, i) => <Pill key={d} pressed={weekdays.includes(i)} onClick={() => toggleDay(i)}>{d}</Pill>)}
              </div>
              <p className="mt-2 text-xs text-muted-foreground">{hours(minutes * weekdays.length)} per week</p>
            </fieldset>
            <Field className="max-w-xs">
              <FieldLabel htmlFor="settings-target">Target date</FieldLabel>
              <Input id="settings-target" type="date" className="h-9" value={targetDate} onChange={e => setTargetDate(e.target.value)} />
              <FieldDescription>Leave empty for no deadline.</FieldDescription>
            </Field>
          </CardContent>
          <CardFooter className="flex flex-wrap items-center gap-3">
            <Button disabled={busy}>{busy ? <Spinner /> : null} Save changes</Button>
            {status ? <span role="status" className="flex items-center gap-1.5 text-sm text-success"><CheckCircle2 className="size-4" /> {status}</span> : null}
          </CardFooter>
        </Card>
      </form>

      <Appearance />
      <CodeforcesLink />

      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Your data</CardTitle>
          <CardDescription>Download everything Socrat stores about you: profile, enrollments, results, code submissions and tutor conversations.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={exportData}><Download data-icon="inline-start" /> Download my data</Button>
          <Button variant="ghost" onClick={async () => { await signOut(); router.replace('/login'); }}><LogOut data-icon="inline-start" /> Sign out</Button>
        </CardContent>
      </Card>

      <Card className="ring-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Delete account</CardTitle>
          <CardDescription>Permanently deletes your account, progress, code and conversations. This cannot be undone.</CardDescription>
        </CardHeader>
        <CardContent>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="destructive"><Trash2 data-icon="inline-start" /> Delete my account</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Delete your account?</AlertDialogTitle>
                <AlertDialogDescription>Your plan, progress, code and tutor conversations will be erased. Type <strong>delete</strong> to confirm.</AlertDialogDescription>
              </AlertDialogHeader>
              <Input value={confirmDelete} onChange={e => setConfirmDelete(e.target.value)} autoComplete="off" aria-label="Type delete to confirm" />
              <AlertDialogFooter>
                <AlertDialogCancel>Keep my account</AlertDialogCancel>
                <AlertDialogAction variant="destructive" disabled={busy || confirmDelete.trim().toLowerCase() !== 'delete'} onClick={deleteAccount}>
                  Delete permanently
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
      {error ? <ErrorNote message={error} /> : null}
    </Page>
  );
}
