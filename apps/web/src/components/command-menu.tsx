'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Kbd } from '@/components/ui/kbd';

const load = () => import('@/components/command-palette');
const CommandPalette = dynamic(load, { ssr: false });

/** ⌘K: jump to any page, lesson or library problem. The dialog loads on first use. */
export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const [used, setUsed] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setUsed(true);
        setOpen(o => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <>
      <Button
        variant="outline"
        className="h-8 w-full justify-start gap-2 bg-muted px-2.5 text-muted-foreground shadow-none sm:w-56 lg:w-64"
        onClick={() => { setUsed(true); setOpen(true); }}
        onPointerEnter={() => void load()}
        onFocus={() => void load()}
        aria-label="Search lessons, problems and pages"
      >
        <Search className="size-3.5" />
        <span className="hidden text-sm font-normal sm:inline">Search…</span>
        <Kbd className="ml-auto hidden sm:inline-flex">⌘K</Kbd>
      </Button>
      {used ? <CommandPalette open={open} setOpen={setOpen} /> : null}
    </>
  );
}
