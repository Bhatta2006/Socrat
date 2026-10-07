export type EditorDiagnostic = { line: number; column?: number; severity: 'error' | 'warning'; message: string };
export interface CodeEditorProps {
  language: 'python' | 'cpp' | 'java';
  value: string;
  onChange(next: string): void;
  onBlur(): void;
  readOnly?: boolean;
  fontSize: number;
  theme: 'light' | 'dark' | 'high-contrast';
  diagnostics?: EditorDiagnostic[];
  ariaLabel: string;
  assistMode: 'learning' | 'independent' | 'assessment';
}
