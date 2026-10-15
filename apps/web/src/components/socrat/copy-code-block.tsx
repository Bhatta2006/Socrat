'use client';

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { LANGUAGE_LABEL } from '@/lib/routes';

/** Code sample with a language chip and a copy button; the block scrolls, the page never does. */
export function CopyCodeBlock({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const label = (lang && (LANGUAGE_LABEL as Record<string, string>)[lang === 'py' ? 'python' : lang]) || lang || 'Code';
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable: the code is still selectable */ }
  }
  return (
    <div className="code-sample not-prose relative" data-code-sample="">
      <div className="absolute top-2.5 right-2.5 z-10 flex items-center gap-1.5">
        <span className="rounded-full border border-border-strong px-2.5 py-0.5 font-sans text-xs font-semibold text-muted-foreground">{label}</span>
        <button
          type="button"
          onClick={copy}
          className="grid size-9 place-items-center rounded-full text-muted-foreground transition-colors hover:bg-raised hover:text-foreground"
          aria-label={copied ? 'Copied' : `Copy ${label} code`}
        >
          {copied ? <Check className="size-4" aria-hidden="true" /> : <Copy className="size-4" aria-hidden="true" />}
        </button>
        <span className="sr-only" role="status">{copied ? 'Copied.' : ''}</span>
      </div>
      <pre data-lang={lang || undefined} tabIndex={0} aria-label={`${label} example`} className="pt-12!"><code>{code}</code></pre>
    </div>
  );
}
