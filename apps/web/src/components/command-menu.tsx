'use client';

import dynamic from 'next/dynamic';
import { useEffect, useState } from 'react';
import { Search } from 'lucide-react';

const load = () => import('@/components/command-palette');
const CommandPalette = dynamic(load, { ssr: false });

/** Ctrl K or ⌘K: jump to any page, lesson or library problem. The dialog loads on first use. */
export function CommandMenu() {
  const [open, setOpen] = useState(false);
  const [used, setUsed] = useState(false);
  const [mac, setMac] = useState(false);

  useEffect(() => {
    setMac(/Mac|iPhone|iPad/.test(navigator.platform));
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === 'k' || e.key === 'K') && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setUsed(true);
        setOpen(o => !o);
      }
    };
    const onSearch = () => { setUsed(true); setOpen(true); };
    window.addEventListener('keydown', onKey);
    window.addEventListener('socrat:search', onSearch);
    return () => { window.removeEventListener('keydown', onKey); window.removeEventListener('socrat:search', onSearch); };
  }, []);

  const show = () => { setUsed(true); setOpen(true); };
  return (
    <>
      {/* Phone: a 44 px icon button. Wider screens: a button that looks like a field. */}
      <button
        type="button"
        onClick={show}
        onPointerEnter={() => void load()}
        onFocus={() => void load()}
        aria-label="Search Socrat"
        data-tour="search"
        className="ml-auto grid size-11 place-items-center rounded-full text-foreground transition-colors hover:bg-raised sm:hidden"
      >
        <Search className="size-5" strokeWidth={1.75} aria-hidden="true" />
      </button>
      <button
        type="button"
        onClick={show}
        onPointerEnter={() => void load()}
        onFocus={() => void load()}
        aria-label="Search Socrat"
        data-tour="search"
        className="hidden h-11 w-64 items-center gap-2.5 rounded-control border border-border-strong bg-card px-4 text-[15px] text-muted-foreground transition-colors hover:border-ring sm:flex lg:w-80"
      >
        <Search className="size-4.5" strokeWidth={1.75} aria-hidden="true" />
        <span className="flex-1 text-left">Search Socrat</span>
        <kbd className="rounded-md border border-border-strong px-1.5 font-sans text-xs">{mac ? '⌘K' : 'Ctrl K'}</kbd>
      </button>
      {used ? <CommandPalette open={open} setOpen={setOpen} /> : null}
    </>
  );
}
