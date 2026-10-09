'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, BookOpen, Check, Code2, Flame, Sparkles, Target, Trophy } from 'lucide-react';
import { api, explain } from '@/lib/api';
import { useGuard, useSession } from '@/lib/session';
import { LANGUAGE_LABEL, hours } from '@/lib/routes';
import type { Course, Language } from '@/lib/types';
import { cn } from '@/lib/utils';
import { ErrorNote, Loading } from '@/components/common';
import { Choice, Pill } from '@/components/choice';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select';
import { Spinner } from '@/components/ui/spinner';

const MINUTES = [15, 20, 30, 45, 60, 90, 120] as const;
const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const ROLES = [
  ['internship', 'Internship'],
  ['new-grad', 'New grad'],
  ['mid-level', 'Mid-level'],
  ['senior', 'Senior'],
] as const;
type Step = 'about' | 'course' | 'level' | 'language' | 'schedule';
const STEP_LABEL: Record<Step, string> = { about: 'You', course: 'Course', level: 'Level', language: 'Language', schedule: 'Schedule' };
const COURSE_ICON: Record<string, typeof BookOpen> = { zero: BookOpen, dsa: Target, cp: Trophy };

function detectTimezone() {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  } catch {
    return 'UTC';
  }
}

function Heading({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-muted-foreground">{body}</p>
    </div>
  );
}

export default function Start() {
  const allowed = useGuard('signed-in');
  const { profile, refresh } = useSession();
  const router = useRouter();
  const [courses, setCourses] = useState<Course[] | null>(null);
  const [step, setStep] = useState<Step>('about');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const [name, setName] = useState('');
  const [birthYear, setBirthYear] = useState('');
  const [birthdayPassed, setBirthdayPassed] = useState(true);
  const [course, setCourse] = useState<Course | null>(null);
  const [level, setLevel] = useState('');
  const [language, setLanguage] = useState<Language | ''>('');
  const [minutes, setMinutes] = useState<number>(30);
  const [weekdays, setWeekdays] = useState<number[]>([0, 1, 2, 3, 4]);
  const [targetDate, setTargetDate] = useState('');
  const [targetRole, setTargetRole] = useState('');
  const [targetRating, setTargetRating] = useState('');
  const [motivation, setMotivation] = useState('');

  useEffect(() => {
    api.get<{ items: Course[] }>('/courses').then(r => setCourses(r.items)).catch(e => setError(explain(e)));
  }, []);
  useEffect(() => {
    if (!profile) return;
    setName(n => n || profile.display_name || '');
    if (profile.birth_year) setStep(s => (s === 'about' ? 'course' : s));
  }, [profile]);

  const thisYear = new Date().getFullYear();
  const years = useMemo(() => Array.from({ length: 90 }, (_, i) => thisYear - 8 - i), [thisYear]);
  const borderline = Number(birthYear) === thisYear - 13;

  async function saveAbout(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.patch('/me', {
        display_name: name.trim() || undefined,
        birth_year: Number(birthYear),
        birthday_passed: borderline ? birthdayPassed : true,
        timezone: detectTimezone(),
      });
      await refresh();
      setStep('course');
    } catch (e) {
      setError(explain(e));
    } finally {
      setBusy(false);
    }
  }

  async function enroll(event: React.FormEvent) {
    event.preventDefault();
    if (!course || !language || !level) return;
    setBusy(true);
    setError('');
    try {
      const body: Record<string, unknown> = { course: course.id, language, level, minutes_per_day: minutes, weekdays };
      if (targetDate) body.target_date = targetDate;
      if (targetRole) body.target_role = targetRole;
      if (targetRating) body.target_rating = Number(targetRating);
      if (motivation.trim()) body.motivation = motivation.trim();
      const result = await api.post<{ status: string }>('/enrollments', body);
      await refresh();
      router.replace(result.status === 'placement' ? '/placement' : '/today');
    } catch (e) {
      setError(explain(e));
      setBusy(false);
    }
  }

  if (!allowed || !courses) return error ? <div className="mx-auto max-w-2xl p-6"><ErrorNote message={error} /></div> : <Loading />;

  const order: Step[] = ['about', 'course', 'level', 'language', 'schedule'];
  const position = order.indexOf(step);
  const back = position > (profile?.birth_year ? 1 : 0) ? () => setStep(order[position - 1]) : undefined;
  const toggleDay = (i: number) => setWeekdays(w => (w.includes(i) ? (w.length > 1 ? w.filter(x => x !== i) : w) : [...w, i].sort()));

  return (
    <div className="mx-auto w-full max-w-2xl px-4 pt-8 pb-24 sm:px-6 md:pt-12">
      {/* Endowed progress: creating the account already counts as a finished step. */}
      <ol className="mb-10 flex items-center gap-2" aria-label="Setup progress">
        <li className="flex items-center gap-2 text-xs font-medium text-success">
          <span className="grid size-6 place-items-center rounded-full bg-success text-success-foreground"><Check className="size-3.5" /></span>
          <span className="hidden sm:inline">Account</span>
        </li>
        {order.map((s, i) => (
          <li key={s} className="flex flex-1 items-center gap-2">
            <span className={cn('h-px flex-1', i <= position ? 'bg-primary' : 'bg-border')} />
            <span
              className={cn(
                'grid size-6 flex-none place-items-center rounded-full border text-[11px] font-semibold',
                i < position && 'border-primary bg-primary text-primary-foreground',
                i === position && 'border-primary text-primary ring-4 ring-primary/15',
                i > position && 'text-muted-foreground',
              )}
            >
              {i < position ? <Check className="size-3.5" /> : i + 1}
            </span>
            <span className={cn('hidden text-xs font-medium sm:inline', i === position ? 'text-foreground' : 'text-muted-foreground')}>{STEP_LABEL[s]}</span>
          </li>
        ))}
      </ol>
      <div className="mb-6 flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">Step {position + 1} of {order.length}</p>
        {back ? <Button type="button" variant="ghost" size="sm" onClick={back}><ArrowLeft data-icon="inline-start" /> Back</Button> : null}
      </div>
      {profile?.enrollment && step === 'course' ? (
        <Alert className="mb-6"><AlertDescription>You&apos;re already enrolled. Starting a new course pauses your current plan; your history is kept.</AlertDescription></Alert>
      ) : null}

      <div key={step} className="animate-in fade-in slide-in-from-bottom-2 duration-300">
        {step === 'about' ? (
          <form onSubmit={saveAbout} className="grid gap-6">
            <Heading title="Let's set you up" body="Two quick details, then you'll choose what to learn." />
            <Field>
              <FieldLabel htmlFor="about-name">What should we call you?</FieldLabel>
              <Input id="about-name" className="h-10 max-w-md" value={name} onChange={e => setName(e.target.value)} maxLength={80} required />
            </Field>
            <Field>
              <FieldLabel htmlFor="about-year">Year you were born</FieldLabel>
              <NativeSelect id="about-year" className="w-full max-w-xs [&_select]:h-10" value={birthYear} onChange={e => setBirthYear(e.target.value)} required>
                <NativeSelectOption value="" disabled>Choose a year</NativeSelectOption>
                {years.map(y => <NativeSelectOption key={y} value={y}>{y}</NativeSelectOption>)}
              </NativeSelect>
              <FieldDescription>Socrat is for learners aged 13 and over. We only store the year.</FieldDescription>
            </Field>
            {borderline ? (
              <label className="flex items-center gap-3 text-sm">
                <Checkbox checked={birthdayPassed} onCheckedChange={v => setBirthdayPassed(v === true)} />
                I&apos;ve already had my birthday this year
              </label>
            ) : null}
            <Button size="lg" className="h-10 justify-self-start px-6" disabled={busy || !birthYear || !name.trim()}>Continue</Button>
          </form>
        ) : null}

        {step === 'course' ? (
          <div className="grid gap-6">
            <Heading title="What do you want to learn?" body="You can switch later. Prerequisites from other courses are pulled in automatically when you need them." />
            <div className="grid gap-3">
              {courses.map(c => {
                const Icon = COURSE_ICON[c.id] ?? Code2;
                return (
                  <Choice
                    key={c.id}
                    icon={<Icon />}
                    selected={course?.id === c.id}
                    aria-pressed={course?.id === c.id}
                    onClick={() => { setCourse(c); setLevel(''); setLanguage(c.languages.length === 1 ? c.languages[0] : ''); setStep('level'); }}
                  >
                    <span className="block text-base font-semibold">{c.title}</span>
                    <span className="block text-sm text-muted-foreground">{c.tagline}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">{c.concept_count} concepts · {c.problem_count} judged problems</span>
                  </Choice>
                );
              })}
            </div>
          </div>
        ) : null}

        {step === 'level' && course ? (
          <div className="grid gap-6">
            <Heading title="How much do you already know?" body="Be honest — if you pick a higher level, a short adaptive check confirms it, so nothing important gets skipped." />
            <div className="grid gap-3">
              {course.levels.map((l, i) => (
                <Choice key={l.id} marker={i + 1} selected={level === l.id} aria-pressed={level === l.id} onClick={() => { setLevel(l.id); setStep('language'); }}>
                  <span className="block font-semibold">{l.label}</span>
                  <span className="block text-sm text-muted-foreground">{l.description}</span>
                </Choice>
              ))}
            </div>
          </div>
        ) : null}

        {step === 'language' && course ? (
          <div className="grid gap-6">
            <Heading title="Which language?" body="Lessons, examples, quizzes and your code editor all follow this choice." />
            <div className="grid gap-3 sm:grid-cols-3">
              {course.languages.map(l => (
                <Choice key={l} selected={language === l} aria-pressed={language === l} className="justify-center py-7" onClick={() => { setLanguage(l); setStep('schedule'); }}>
                  <span className="block text-center text-lg font-semibold">{LANGUAGE_LABEL[l]}</span>
                </Choice>
              ))}
            </div>
          </div>
        ) : null}

        {step === 'schedule' && course ? (
          <form onSubmit={enroll} className="grid gap-8">
            <Heading title="When can you study?" body="Your plan fits into this budget. Missed days never pile up — the plan re-flows instead." />
            <fieldset>
              <legend className="mb-3 text-sm font-medium">Time per study day</legend>
              <div className="flex flex-wrap gap-2">
                {MINUTES.map(m => <Pill key={m} pressed={minutes === m} onClick={() => setMinutes(m)}>{hours(m)}</Pill>)}
              </div>
            </fieldset>
            <fieldset>
              <legend className="mb-3 text-sm font-medium">Study days</legend>
              <div className="flex flex-wrap gap-2">
                {DAYS.map((d, i) => <Pill key={d} pressed={weekdays.includes(i)} onClick={() => toggleDay(i)}>{d}</Pill>)}
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-sm text-muted-foreground">
                <Flame className="size-4 text-streak" /> {hours(minutes * weekdays.length)} per week — a pace you can keep.
              </p>
            </fieldset>
            <div className="grid gap-5 sm:grid-cols-2">
              <Field>
                <FieldLabel htmlFor="target-date">Target date <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                <Input id="target-date" type="date" className="h-10" value={targetDate} min={new Date().toISOString().slice(0, 10)} onChange={e => setTargetDate(e.target.value)} />
              </Field>
              {course.id === 'dsa' ? (
                <Field>
                  <FieldLabel htmlFor="target-role">Interviewing for <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                  <NativeSelect id="target-role" className="w-full [&_select]:h-10" value={targetRole} onChange={e => setTargetRole(e.target.value)}>
                    <NativeSelectOption value="">No specific role</NativeSelectOption>
                    {ROLES.map(([id, label]) => <NativeSelectOption key={id} value={id}>{label}</NativeSelectOption>)}
                  </NativeSelect>
                </Field>
              ) : null}
              {course.id === 'cp' ? (
                <Field>
                  <FieldLabel htmlFor="target-rating">Target rating <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
                  <Input id="target-rating" type="number" className="h-10" min={0} max={4000} step={50} value={targetRating} onChange={e => setTargetRating(e.target.value)} placeholder="e.g. 1600" />
                </Field>
              ) : null}
            </div>
            <Field>
              <FieldLabel htmlFor="motivation">Why are you learning this? <span className="font-normal text-muted-foreground">(optional)</span></FieldLabel>
              <Input id="motivation" className="h-10" value={motivation} onChange={e => setMotivation(e.target.value)} maxLength={280} placeholder="Your tutor will keep this in mind" />
            </Field>
            <Button size="lg" className="h-11 justify-self-start px-6 shadow-lg shadow-primary/20" disabled={busy}>
              {busy ? <><Spinner /> Building your plan…</> : <><Sparkles data-icon="inline-start" /> Build my plan</>}
            </Button>
          </form>
        ) : null}
      </div>

      {error ? <ErrorNote message={error} /> : null}
    </div>
  );
}
