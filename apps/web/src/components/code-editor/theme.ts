import { HighlightStyle } from '@codemirror/language';
import { EditorView } from '@codemirror/view';
import { tags as t } from '@lezer/highlight';

/** Editor chrome and syntax colours tuned to Socrat's tokens; every pair meets WCAG AA. */
type Palette = {
  bg: string; fg: string; gutter: string; gutterFg: string; border: string; selection: string;
  activeLine: string; cursor: string; focus: string; keyword: string; string: string; number: string;
  comment: string; fn: string; type: string; constant: string; operator: string; punctuation: string;
};

const LIGHT: Palette = {
  bg: '#ffffff', fg: '#1f2329', gutter: '#f6f7f9', gutterFg: '#6b7280', border: '#e4e6ea',
  selection: '#cfe8dc', activeLine: '#f3f8f5', cursor: '#0f766e', focus: '#10805d',
  keyword: '#7c3aed', string: '#15803d', number: '#b45309', comment: '#6b7280', fn: '#1d4ed8',
  type: '#c2410c', constant: '#be123c', operator: '#374151', punctuation: '#4b5563',
};
const DARK: Palette = {
  bg: '#16181d', fg: '#e6e8eb', gutter: '#16181d', gutterFg: '#7d8592', border: '#2a2e36',
  selection: '#2f4a3f', activeLine: '#1d2128', cursor: '#5eead4', focus: '#34d399',
  keyword: '#c4a7ff', string: '#9ee6a3', number: '#ffcf7a', comment: '#8b93a1', fn: '#7cc7ff',
  type: '#ffb07c', constant: '#ff9ea8', operator: '#d4d7dd', punctuation: '#aab1bd',
};
const CONTRAST: Palette = {
  ...DARK, bg: '#000000', gutter: '#000000', fg: '#ffffff', gutterFg: '#e5e7eb', border: '#ffffff',
  comment: '#d1d5db', focus: '#ffd45c', selection: '#3f5a50',
};

function highlight(p: Palette) {
  return HighlightStyle.define([
    { tag: [t.keyword, t.controlKeyword, t.moduleKeyword, t.operatorKeyword, t.definitionKeyword], color: p.keyword },
    { tag: [t.string, t.special(t.string), t.character, t.regexp], color: p.string },
    { tag: [t.number, t.integer, t.float], color: p.number },
    { tag: [t.comment, t.lineComment, t.blockComment, t.docComment], color: p.comment, fontStyle: 'italic' },
    { tag: [t.function(t.variableName), t.function(t.propertyName), t.macroName], color: p.fn },
    { tag: [t.typeName, t.className, t.namespace, t.standard(t.typeName)], color: p.type },
    { tag: [t.bool, t.null, t.atom, t.self, t.constant(t.variableName)], color: p.constant },
    { tag: [t.operator, t.compareOperator, t.arithmeticOperator, t.logicOperator], color: p.operator },
    { tag: [t.punctuation, t.bracket, t.separator], color: p.punctuation },
    { tag: [t.definition(t.variableName), t.variableName, t.propertyName], color: p.fg },
    { tag: t.invalid, color: p.constant, textDecoration: 'underline wavy' },
  ]);
}

export const HIGHLIGHT = { light: highlight(LIGHT), dark: highlight(DARK), 'high-contrast': highlight(CONTRAST) };

export function chrome(theme: 'light' | 'dark' | 'high-contrast', fontSize: number) {
  const p = theme === 'light' ? LIGHT : theme === 'dark' ? DARK : CONTRAST;
  return EditorView.theme(
    {
      '&': { height: '100%', color: p.fg, backgroundColor: p.bg, fontSize: `${fontSize}px` },
      '.cm-scroller': { overflow: 'auto', fontFamily: 'var(--font-mono), Consolas, monospace', lineHeight: '1.65' },
      '.cm-content': { minHeight: '100%', caretColor: p.cursor, padding: '10px 0' },
      '.cm-gutters': { color: p.gutterFg, backgroundColor: p.gutter, borderRight: `1px solid ${p.border}` },
      '.cm-activeLine': { backgroundColor: p.activeLine },
      '.cm-activeLineGutter': { backgroundColor: p.activeLine, color: p.fg },
      '&.cm-focused': { outline: `2px solid ${p.focus}`, outlineOffset: '-2px' },
      '.cm-cursor, .cm-dropCursor': { borderLeftColor: p.cursor, borderLeftWidth: '2px' },
      '.cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection': { backgroundColor: p.selection },
      '.cm-matchingBracket': { backgroundColor: p.selection, outline: `1px solid ${p.focus}` },
      '.cm-tooltip': { backgroundColor: p.bg, color: p.fg, border: `1px solid ${p.border}`, borderRadius: '8px' },
      '.cm-tooltip-autocomplete > ul > li[aria-selected]': { backgroundColor: p.selection, color: p.fg },
      '.cm-lint-marker': { outline: theme === 'high-contrast' ? '1px solid #fff' : 'none' },
    },
    { dark: theme !== 'light' },
  );
}
