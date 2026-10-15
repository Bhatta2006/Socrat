# Socrat design system: "Learn it. Then prove it."

This is the reference for the web app's visual system after the redesign. Tokens live in
`apps/web/src/app/globals.css`. Shared components live in `apps/web/src/components/socrat/`,
and restyled primitives in `apps/web/src/components/ui/`. A live gallery of every component
renders at `/dev-gallery` in development; production builds return 404 for it.

## Principles

1. Each content screen has one violet hero card or one violet primary action.
2. Lime marks only states the backend records as mastery or review due. It is never used on a
   button or as a background.
3. Every status is shown as shape, label and colour together, never colour alone.
4. Depth comes from surface steps and hairlines. There are no shadows except on floating
   elements, and no gradients or blur.
5. Every number, chart and status shown comes from real data.

## Tokens

The `:root` (light) and `.dark` blocks hold everything the playground compiler
(`services/api/src/socrat/explainer/artifact.py`) injects into generated visuals. That compiler
reads both blocks with a column-0 regex, so keep their shape. Host-only tokens (proof, status
ring overrides, mark and illustration colours) sit in separate `html:root` and `html.dark`
blocks, so lime never reaches a generated document. `services/api/tests/test_explainer.py`
asserts this.

| Role | Variable | Dark | Light |
| --- | --- | --- | --- |
| Canvas | `--background` | `#0E0D14` | `#F6F4FA` |
| Card | `--card` | `#17151F` | `#FFFFFF` |
| Raised (also popover in dark, muted) | `--raised` | `#211E2B` | `#EFECF6` |
| Hairline | `--border` | `#2A2735` | `#DDD9E8` |
| Strong hairline (also `--input`) | `--border-strong` | `#3A3649` | `#C4BFD4` |
| Text | `--foreground` | `#E9E6F2` | `#17151F` |
| Muted text | `--muted-foreground` | `#9A94AD` | `#55616B` |
| Violet | `--primary` / `--primary-foreground` | `#7D39EB` / `#F4F2FA` | `#6A2BD6` / `#FFFFFF` |
| Violet as text (links, selected marks) | `--brand-text` | `#B9A6F5` | `#6A2BD6` |
| Lilac | `--secondary` / `--secondary-foreground` | `#B9A6F5` / `#17151F` | same |
| Cream | `--cream` / `--cream-foreground` | `#F4F2FA` / `#17151F` | `#E9E4F6` / `#17151F` |
| Ink (pill on colour) | `--ink` / `--ink-foreground` | `#0E0D14` / `#E9E6F2` | `#17151F` / `#F6F4FA` |
| Proof (host only) | `--proof` / `--proof-foreground` / `--proof-stroke` | `#C6FF33` / `#0E0D14` / `#0E0D14` | `#C6FF33` / `#17151F` / `#17151F` |
| Attention | `--attention` (alias `--destructive`, `--warning`) | `#F08A86` | `#C4453F` |
| Focus ring | `--ring` | `#B9A6F5` | `#6A2BD6` |
| Heatmap ramp | `--heat-0` to `--heat-4` | `#211E2B` to `#B9A6F5` | `#EFECF6` to `#6A2BD6` |
| Syntax | `--syntax-*` | spec section 5 | spec section 5 |

Retired meanings are kept as aliases so nothing renders unstyled. `success` is the foreground
colour (always shown with a check and a label), and `warning` is attention. Amber, green, sky
and emerald are gone.

Deviations from the spec's values, and why:

- **`--brand-text`.** Violet `#7D39EB` measures 3.1:1 as text on the dark card, so violet text
  in dark mode uses lilac instead.
- **`--status-practised` is `#9A63F2` in dark.** `#7D39EB` is 2.9:1 on the raised surface, and
  status rings need 3:1.
- **Light `chart-2` and `chart-3` are `#8A55E6` and ink.** The spec's light cream chart colour
  is about 1.2:1 on white and fails the 3:1 contrast rule for diagram strokes.
- **On the violet hero, secondary text is solid cream.** Translucent cream failed 4.5:1, so
  hierarchy on violet comes from size and weight instead.

### Type

| Token | Family | Size (mobile / desktop) |
| --- | --- | --- |
| `type-display-xl` | Display, 700, −0.035em | 52/52 → 112/104 |
| `type-display-l` | Display, 700 | 44/46 → 56/56 |
| `type-display-m` | Display, 700 | 32/34 → 40/42 |
| `type-title` | Display, 650 | 22/28 → 24/30 |
| `type-body-l` | Body | 17/28 → 18/30 |
| body | Figtree 500 | 16/24 |
| `type-label` | Body 600, caps, 0.14em | 11/14 |
| code | JetBrains Mono, ligatures off | 14/22 |

The display face is Geist Sans Bold, the spec's sanctioned fallback for General Sans (see the
report for why). Figtree and JetBrains Mono are vendored in `apps/web/src/fonts/` under SIL OFL
1.1, so builds need no font network access.

### Space, radius, motion

- **Radius:** `rounded-card` 28 px, `rounded-inner` 20 px, `rounded-control` 16 px, pills
  `rounded-full`. Base `--radius` is 1rem.
- **Page padding:** 16, 24 and 40 px. Bento gaps: 12, 16 and 24 px.
- **Card padding:** 20 and 24 px; hero cards 24 and 32 px.
- **Shadows:** `shadow-floating` only, for dialogs, popovers, the tutor launcher and the arrow
  button.
- **Motion:** 120, 200 and 320 ms with `--ease-soft`
  (`cubic-bezier(0.2, 0.8, 0.2, 1)`). Allowed: fades, 8 px rises, a 0.98 press scale, the
  arrow nudge and ring draw.
- **Reduced motion:** all motion stops under `prefers-reduced-motion` or the in-app setting
  (`html[data-reduce-motion="true"]`, set from Settings and applied before first paint by
  `lib/motion.ts`).
- **Focus:** a 2 px `--ring` outline with 2 px offset on every `:focus-visible` element.

## Status system

`components/socrat/status.tsx` provides `StatusIcon`, `StatusLabel`, `StatusLegend`,
`statusFromRoadmap` and `statusFromBand`.

| State | Shape | Label | Roadmap source (`/plan`) | Band source (`/progress`, concept views) |
| --- | --- | --- | --- | --- |
| Not seen | dashed circle | Not seen yet | `upcoming`, lesson not read | `not_started` |
| Locked | rounded square with lock | Locked until {checkpoint} | `locked` (`locked_by`) | concept `locked` |
| Read | ring with centre dot | Read | `upcoming` or `in_progress`, lesson read, check not done | — |
| Assumed | lower-half-filled ring, 60% | Assumed from placement | `assumed` | `likely_known` |
| Practised with help | 2.5 px violet ring | Practised with help | `practiced`, or `in_progress` with check done or evidence | `developing` |
| Mastered | lime disc with ink check | Mastered | `mastered` | `strong` |
| Review due | lime dotted ring | Review due | `review_due` (badge beside the base state) | `next_review` ≤ now |
| Needs practice | coral triangle | Needs practice | — | `needs_practice` |

The lime disc is labelled **Mastered**, not "Shown independently". The mastery estimate
(`mastery/model.py`) also counts assisted successes, at reduced weight. "Independent" appears
only where the data records it: per-result `assisted == false` on the Evidence timeline, and
`independent_solves` (accepted code submissions at assistance level 0).

## Components

| Component | File | Notes |
| --- | --- | --- |
| Button | `ui/button.tsx` | Variants: `default` (violet pill), `ink` (on colour), `outline` (secondary), `ghost`, `link`, `run`, `destructive` (outlined coral), `attention` (filled coral confirm). 44 px default, 52/48 px `lg`. `ArrowCircle` gives the circular arrow and doubles as the loading spinner. |
| Card | `ui/card.tsx` | `tone`: `surface`, `hero`, `lilac`, `cream` (lilac in light), `raised`, `outlined`. A labelled card becomes `role="region"`. Colour tones set `--card-muted` and status overrides. |
| Badge (chip) | `ui/badge.tsx` | Outlined 28 px pill. Inherits the text colour inside any `[data-tone]` container. |
| Inputs | `ui/input.tsx`, `ui/textarea.tsx`, `ui/native-select.tsx` | 52 px, 16 px radius, card fill, strong hairline. |
| Segmented control | `ui/tabs.tsx`, `socrat/practice-nav.tsx` | Pill track on raised; selected segment on card with a hairline and bold label. Practice segments are real links. |
| Dialogs and sheets | `ui/dialog.tsx`, `ui/alert-dialog.tsx`, `ui/sheet.tsx` | 28 px radius, solid 60% ink scrim, no blur. Bottom sheets have a drag handle and a 44 px Close. Alert dialogs focus Cancel first. |
| Table | `ui/table.tsx` | 56 px rows, sticky caps header, tabular numerals. Phones get card rows instead. |
| States | `socrat/states.tsx` | `EmptyState`, `ErrorState` (coral triangle, retry, inline), `LockedState`, `SuccessLine`, `AttentionIcon`. |
| Brand | `socrat/wordmark.tsx`, `app/icon.svg` | Two offset half-discs (violet over cream, or lilac in light) and "Socrat" in the display face. |
| Illustration | `socrat/illustration.tsx` | `welcome`, `orbit`, `stack`, `ladder`, `empty`, plus the `Soc` tutor line drawing. Token-coloured and `aria-hidden`. Lime only as the one dot in `welcome`. |
| Skill map | `socrat/node-map.tsx` | Map/List toggle, labelled "Order in module" (no prerequisite edges exist). List is the default under 480 px. |
| Week strip | `socrat/week-strip.tsx` | Today in a violet pill. A dot marks study only when `studied_today`. |
| Arrow button | `socrat/arrow-button.tsx` | Round 56/44 px. Ink on colour, violet on neutral. |
| Code block | `socrat/copy-code-block.tsx` | Language chip, copy button and focusable scroll region. Used by the lesson Markdown renderer. |
| Ring, stat card, difficulty | `components/common.tsx` | Difficulty is an outlined chip with a 1–3 bar glyph, not colour-coded. |

## Navigation

`lib/routes.ts` holds the canonical names (`NAME`), the six destinations (`NAV`), the Practice
segments and `navFor()`. Routes keep their paths.

| Item | Route | Owns |
| --- | --- | --- |
| Today | `/today` | — |
| Skills | `/plan` | `/learn`, `/quiz` |
| Practice | `/library` | `/companies`, `/sprint`, `/problems` |
| Playground | `/playground` | — |
| Evidence | `/progress` | `/assessments` |
| Settings | `/settings` | — |

Layout by width:

- **Desktop (≥1024 px):** 248 px sidebar, collapsible to a 72 px rail.
- **Tablet (768–1023 px):** rail only.
- **Phone:** five-item bottom nav, with Settings in the avatar menu. The Soc tutor launcher
  sits 16 px above the nav, and pages with their own "Ask Soc" control show it on phones only.

## Checks that guard the system

- `tests/e2e/accessibility.spec.ts`: axe WCAG 2.1 AA on every main route, light and dark.
- `tests/e2e/keyboard.spec.ts`: a full keyboard session, focus ring on every stop, one `h1`
  per page with no skipped heading levels.
- `tests/e2e/layout.spec.ts`: no page-level horizontal overflow at 320, 390, 768 and 1440 px.
- `tests/visual/pages.spec.ts`: screenshot baselines in `tests/visual/__screenshots__/win32`.
- `services/api/tests/test_explainer.py`: the generated-visual palette carries the new tokens
  and never contains the proof colour.
