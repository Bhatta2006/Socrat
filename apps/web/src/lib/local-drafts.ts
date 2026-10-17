/**
 * A copy of each problem draft in this browser, so code typed offline or in a tab that closed
 * before the autosave survives. `synced` says whether the server has this exact text.
 */
type LocalDraft = { source: string; at: number; synced: boolean };

const key = (problemId: string, language: string) => `socrat:draft:${problemId}:${language}`;

export function readLocalDraft(problemId: string, language: string): LocalDraft | null {
  try {
    const raw = localStorage.getItem(key(problemId, language));
    return raw ? (JSON.parse(raw) as LocalDraft) : null;
  } catch {
    return null;
  }
}

export function writeLocalDraft(problemId: string, language: string, source: string, synced: boolean) {
  try {
    localStorage.setItem(key(problemId, language), JSON.stringify({ source, at: Date.now(), synced }));
  } catch {
    /* storage full or blocked: the server autosave still runs */
  }
}
