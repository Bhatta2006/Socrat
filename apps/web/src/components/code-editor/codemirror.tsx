'use client';
import { useEffect, useRef } from 'react';
import { Compartment, EditorState } from '@codemirror/state';
import { EditorView, keymap, lineNumbers, highlightActiveLineGutter } from '@codemirror/view';
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands';
import { bracketMatching, indentOnInput, indentUnit, syntaxHighlighting, defaultHighlightStyle } from '@codemirror/language';
import { autocompletion, closeBrackets, closeBracketsKeymap, completionKeymap, completeFromList } from '@codemirror/autocomplete';
import { search, searchKeymap, highlightSelectionMatches } from '@codemirror/search';
import { lintGutter, setDiagnostics } from '@codemirror/lint';
import { python } from '@codemirror/lang-python';
import { cpp } from '@codemirror/lang-cpp';
import { java } from '@codemirror/lang-java';
import type { CodeEditorProps } from './types';

const keywords = {
  python: 'def return if else elif for while in and or not True False None class import from',
  cpp: 'int long bool void return if else for while const struct class true false',
  java: 'public private static class int long boolean void return if else for while true false null',
};
function options(props: CodeEditorProps) {
  const dark = props.theme !== 'light';
  const contrast = props.theme === 'high-contrast';
  return [
    EditorState.readOnly.of(Boolean(props.readOnly)), EditorView.editable.of(!props.readOnly),
    EditorView.contentAttributes.of({ 'aria-label': props.ariaLabel, 'aria-describedby': 'editor-keyboard-help' }),
    EditorView.theme({
      '&': { height: '100%', color: dark ? '#ffffff' : '#182a24', backgroundColor: dark ? (contrast ? '#000000' : '#17251f') : '#fffdf7', fontSize: `${props.fontSize}px` },
      '.cm-scroller': { overflow: 'auto', fontFamily: 'Consolas, monospace' },
      '.cm-content': { minHeight: '100%', caretColor: dark ? '#fff' : '#182a24' },
      '.cm-gutters': { color: dark ? '#f4f1d6' : '#424c42', backgroundColor: dark ? '#17251f' : '#f2eee2', borderRight: '1px solid #92998f' },
      '&.cm-focused': { outline: `3px solid ${dark ? '#ffd45c' : '#316047'}`, outlineOffset: '-3px' },
      '.cm-cursor': { borderLeftColor: dark ? '#fff' : '#182a24' },
      '.cm-selectionBackground, &.cm-focused .cm-selectionBackground': { backgroundColor: dark ? '#445f52' : '#c8decb' },
      '.cm-lint-marker': { outline: contrast ? '1px solid #fff' : 'none' },
    }, { dark }),
    props.assistMode === 'learning' ? autocompletion({ override: [completeFromList(keywords[props.language].split(' ').map(label => ({ label, type: 'keyword' })))] }) : [],
  ];
}

export default function CodeMirror(props: CodeEditorProps) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const current = useRef(props); current.current = props;
  const configuration = useRef(new Compartment());
  useEffect(() => {
    if (!host.current) return;
    const instance = new EditorView({ parent: host.current, state: EditorState.create({ doc: current.current.value, extensions: [
      { python, cpp, java }[current.current.language](), lineNumbers(), highlightActiveLineGutter(),
      history(), search(), highlightSelectionMatches(), bracketMatching(), indentOnInput(), closeBrackets(),
      indentUnit.of('    '), EditorState.tabSize.of(4), EditorView.lineWrapping,
      syntaxHighlighting(defaultHighlightStyle), lintGutter(),
      keymap.of([{ key: 'Escape', run: editor => { editor.setTabFocusMode(10000); return true; } }, ...closeBracketsKeymap, ...defaultKeymap, ...historyKeymap, ...searchKeymap, ...completionKeymap, indentWithTab]),
      configuration.current.of(options(current.current)),
      EditorView.updateListener.of(update => { if (update.docChanged) current.current.onChange(update.state.doc.toString()); }),
      EditorView.domEventHandlers({ blur: () => { current.current.onBlur(); } }),
    ] }) });
    view.current = instance;
    return () => { instance.destroy(); view.current = null; };
  }, [props.language]);
  useEffect(() => {
    const editor = view.current; if (!editor) return;
    if (editor.state.doc.toString() !== props.value) editor.dispatch({ changes: { from: 0, to: editor.state.doc.length, insert: props.value } });
    editor.dispatch({ effects: configuration.current.reconfigure(options(props)) });
    editor.dispatch(setDiagnostics(editor.state, (props.diagnostics ?? []).filter(d => d.line >= 1 && d.line <= editor.state.doc.lines).map(d => {
      const line = editor.state.doc.line(d.line);
      const from = Math.min(line.to, line.from + Math.max(0, (d.column ?? 1) - 1));
      return { from, to: Math.min(line.to, from + 1), severity: d.severity, message: d.message };
    })));
  }, [props.value, props.readOnly, props.fontSize, props.theme, props.assistMode, props.language, props.ariaLabel, props.diagnostics]);
  return <div ref={host} className="code-editor-host w-full min-w-0 overflow-hidden" data-testid="code-editor" data-editor-theme={props.theme} data-assist-mode={props.assistMode} />;
}
