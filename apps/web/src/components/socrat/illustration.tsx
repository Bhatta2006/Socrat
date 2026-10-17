import { cn } from '@/lib/utils';

/**
 * Flat geometric compositions: circles, half-circles, rounded squares and arcs with an
 * occasional 1.5 px line. Colours come from tokens so both themes work. Never contain text.
 * Lime appears only as one small dot, and only in `welcome` (landing and login).
 */
export type IllustrationName = 'stack' | 'orbit' | 'welcome' | 'ladder' | 'empty';

const V = 'var(--primary)';
const L = 'var(--secondary)';
const C = 'var(--mark-cream)';
const I = 'var(--ink)';
const LINE = 'var(--illo-line)';

function Welcome({ proof }: { proof: boolean }) {
  return (
    <>
      <rect x="18" y="64" width="128" height="128" rx="32" fill={V} />
      <path d="M150 60a74 74 0 0 1 0 148Z" fill={C} />
      <path d="M84 196a66 66 0 0 1 132 0" fill="none" stroke={L} strokeWidth="22" />
      <circle cx="198" cy="58" r="22" fill={I} />
      {proof ? <circle cx="62" cy="40" r="7" fill="var(--proof)" stroke="var(--proof-stroke)" strokeWidth="1.5" /> : null}
      <path d="M10 150c40-46 96-60 150-30s70 10 82-14" fill="none" stroke={LINE} strokeWidth="1.5" strokeLinecap="round" />
      <path d="M40 222c34-26 78-30 118-12" fill="none" stroke={LINE} strokeWidth="1.5" strokeLinecap="round" />
    </>
  );
}

function Orbit() {
  return (
    <>
      <circle cx="140" cy="120" r="88" fill="none" stroke={L} strokeWidth="1.5" />
      <path d="M52 120a88 88 0 0 1 176 0" fill="none" stroke={C} strokeWidth="18" strokeLinecap="round" />
      <circle cx="140" cy="120" r="46" fill={I} />
      <path d="M140 74a46 46 0 0 1 0 92Z" fill={L} />
      <circle cx="52" cy="120" r="14" fill={C} />
      <path d="M20 200c50-30 120-36 200-6" fill="none" stroke={LINE} strokeWidth="1.5" strokeLinecap="round" />
    </>
  );
}

function Stack() {
  return (
    <>
      <rect x="40" y="128" width="112" height="64" rx="20" fill={C} />
      <rect x="72" y="84" width="112" height="64" rx="20" fill={L} />
      <rect x="104" y="40" width="96" height="64" rx="20" fill={I} />
      <circle cx="176" cy="172" r="26" fill={I} />
      <path d="M176 146a26 26 0 0 1 0 52Z" fill={C} />
      <path d="M24 70c30 10 50 40 52 74" fill="none" stroke={LINE} strokeWidth="1.5" strokeLinecap="round" />
    </>
  );
}

function Ladder() {
  return (
    <>
      <rect x="28" y="152" width="48" height="56" rx="16" fill={C} />
      <rect x="88" y="112" width="48" height="96" rx="16" fill={L} />
      <rect x="148" y="64" width="48" height="144" rx="16" fill={I} />
      <path d="M172 64a24 24 0 0 1 24-24v0" fill="none" stroke={LINE} strokeWidth="1.5" />
      <circle cx="172" cy="36" r="14" fill={C} />
      <path d="M20 132c40-56 110-86 196-94" fill="none" stroke={LINE} strokeWidth="1.5" strokeLinecap="round" strokeDasharray="2 6" />
    </>
  );
}

function Empty() {
  return (
    <>
      <circle cx="120" cy="120" r="72" fill="none" stroke="var(--border-strong)" strokeWidth="1.5" strokeDasharray="6 7" />
      <path d="M120 72a48 48 0 0 1 0 96Z" fill={L} />
      <path d="M120 72a48 48 0 0 0 0 96Z" fill={C} opacity="0.55" />
    </>
  );
}

export function Illustration({ name, className, proof = false }: { name: IllustrationName; className?: string; proof?: boolean }) {
  return (
    <svg viewBox="0 0 240 240" className={cn('block', className)} aria-hidden="true" focusable="false">
      {name === 'welcome' ? <Welcome proof={proof} /> : name === 'orbit' ? <Orbit /> : name === 'stack' ? <Stack /> : name === 'ladder' ? <Ladder /> : <Empty />}
    </svg>
  );
}

/**
 * Soc, the tutor: a round, bearded purple face (public/soc, made by scripts/make-soc.mjs).
 * Decorative unless `label` is given (only where it acts as a control). Inside a button or
 * link, Soc nods when it is hovered or focused (see .soc-avatar in globals.css).
 */
export function Soc({ size = 48, className, label }: { size?: number; className?: string; label?: string }) {
  const source = size <= 48 ? 96 : size <= 96 ? 192 : 384;
  return (
    // eslint-disable-next-line @next/next/no-img-element -- a fixed-size local asset; no loader needed
    <img
      src={`/soc/soc-${source}.webp`}
      width={size}
      height={size}
      alt={label ?? ''}
      aria-hidden={label ? undefined : true}
      draggable={false}
      decoding="async"
      className={cn('soc-avatar flex-none select-none', className)}
    />
  );
}
