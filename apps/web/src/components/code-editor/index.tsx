'use client';
import dynamic from 'next/dynamic';
const CodeEditor = dynamic(() => import('./codemirror'), { ssr: false, loading: () => <p role="status">Loading editor…</p> });
export default CodeEditor;
export type { CodeEditorProps, EditorDiagnostic } from './types';
