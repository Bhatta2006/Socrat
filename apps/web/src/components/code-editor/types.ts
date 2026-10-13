export type EditorDiagnostic = { line: number; column?: number; severity: 'error' | 'warning'; message: string };
export interface CodeEditorProps {
  language: 'python' | 'cpp' | 'java';
  value: string;
  onChange(next: string): void;
  onBlur(): void;
  readOnly?: boolean;
  fontSize: number;
  /** Spaces per indent level (default 4). */
  tabSize?: number;
  theme: 'light' | 'dark' | 'high-contrast';
  diagnostics?: EditorDiagnostic[];
  ariaLabel: string;
  assistMode: 'learning' | 'independent' | 'assessment';
  /** Ctrl/Cmd+Enter. */
  onRun?(): void;
  /** Ctrl/Cmd+Shift+Enter. */
  onSubmit?(): void;
}
