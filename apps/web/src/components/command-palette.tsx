'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { BookOpen, CalendarCheck, CalendarDays, Timer, ChartLine, Home, Library, Settings, Building2 } from 'lucide-react';
import { api } from '@/lib/api';
import { conceptHref } from '@/lib/routes';
import type { LibraryProblem } from '@/lib/types';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';

const PAGES = [
  { href: '/today', label: 'Today', icon: Home },
  { href: '/plan', label: 'Plan', icon: CalendarDays },
  { href: '/library', label: 'Practice library', icon: Library },
  { href: '/assessments', label: 'Weekly assessment', icon: CalendarCheck },
  { href: '/sprint', label: 'Focus sprint', icon: Timer },
  { href: '/progress', label: 'Progress', icon: ChartLine },
  { href: '/companies', label: 'Company question bank', icon: Building2 },
  { href: '/settings', label: 'Settings', icon: Settings },
];

interface Concept { id: string; title: string; course: string }

/** The ⌘K dialog; loaded on first use so cmdk stays out of every page's bundle. */
export default function CommandPalette({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [concepts, setConcepts] = useState<Concept[]>([]);
  const [problems, setProblems] = useState<LibraryProblem[]>([]);

  useEffect(() => {
    if (!open || concepts.length) return;
    api.get<{ concepts: Concept[] }>('/library/meta').then(m => setConcepts(m.concepts)).catch(() => undefined);
  }, [open, concepts.length]);
  useEffect(() => {
    if (!open || query.trim().length < 2) { setProblems([]); return; }
    const timer = setTimeout(() => {
      api.get<{ items: LibraryProblem[] }>(`/library?q=${encodeURIComponent(query.trim())}&sort=popular&limit=6`)
        .then(r => setProblems(r.items))
        .catch(() => undefined);
    }, 200);
    return () => clearTimeout(timer);
  }, [open, query]);

  function go(href: string) {
    setOpen(false);
    setQuery('');
    if (href.startsWith('http')) window.open(href, '_blank', 'noopener,noreferrer');
    else router.push(href);
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen} title="Search Socrat" description="Jump to a page, lesson or problem">
      <Command>
      <CommandInput placeholder="Search lessons, problems, pages…" value={query} onValueChange={setQuery} />
      <CommandList>
        <CommandEmpty>No results. Try another word.</CommandEmpty>
        <CommandGroup heading="Pages">
          {PAGES.map(p => (
            <CommandItem key={p.href} value={`page ${p.label}`} onSelect={() => go(p.href)}>
              <p.icon /> {p.label}
            </CommandItem>
          ))}
        </CommandGroup>
        {problems.length ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Problems">
              {problems.map(p => (
                <CommandItem key={p.id} value={`problem ${p.title} ${query}`} onSelect={() => go(p.url)}>
                  <span className="truncate">{p.title}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{p.platform}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        ) : null}
        {concepts.length ? (
          <>
            <CommandSeparator />
            <CommandGroup heading="Lessons">
              {concepts.map(c => (
                <CommandItem key={c.id} value={`lesson ${c.title} ${c.course}`} onSelect={() => go(conceptHref(c.id))}>
                  <BookOpen /> <span className="truncate">{c.title}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{c.course}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        ) : null}
      </CommandList>
      </Command>
    </CommandDialog>
  );
}
