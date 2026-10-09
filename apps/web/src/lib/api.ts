'use client';

/** Thin client for the v2 learner API. Writes carry the session's CSRF token. */

export class ApiError extends Error {
  constructor(public status: number, public code: string) {
    super(code);
  }
}

let csrf = '';
export function setCsrf(token: string) {
  csrf = token;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (method !== 'GET') headers['X-CSRF-Token'] = csrf;
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    credentials: 'same-origin',
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, data?.error?.code ?? 'request_failed');
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body: unknown = {}) => request<T>('POST', path, body),
  put: <T>(path: string, body: unknown) => request<T>('PUT', path, body),
  patch: <T>(path: string, body: unknown) => request<T>('PATCH', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};

export type StreamEvent = { event: string; data: Record<string, unknown> };

/** POST that answers with Server-Sent Events; yields each parsed event. */
export async function* stream(path: string, body: unknown): AsyncGenerator<StreamEvent> {
  const response = await fetch(`/api/v1${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf },
    credentials: 'same-origin',
    body: JSON.stringify(body),
  });
  if (!response.ok || !response.body) {
    const data = await response.json().catch(() => ({}));
    throw new ApiError(response.status, data?.error?.code ?? 'request_failed');
  }
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let split;
    while ((split = buffer.indexOf('\n\n')) >= 0) {
      const chunk = buffer.slice(0, split);
      buffer = buffer.slice(split + 2);
      let event = 'message';
      let data = '';
      for (const line of chunk.split('\n')) {
        if (line.startsWith('event: ')) event = line.slice(7);
        else if (line.startsWith('data: ')) data += line.slice(6);
      }
      if (data) yield { event, data: JSON.parse(data) };
    }
  }
}

const MESSAGES: Record<string, string> = {
  minimum_age: 'Socrat is for learners aged 13 and over.',
  profile_incomplete: 'Finish your profile first.',
  content_unavailable: 'Course content is not built yet. Run python scripts/content/build.py.',
  assistant_daily_limit: "You've reached today's assistant limit. It resets within 24 hours.",
  execution_unavailable: 'Code execution is turned off on this server.',
  runtime_offline: 'No code runner for this language is online right now. Try again shortly.',
  daily_run_quota: "You've used today's run allowance. It resets tomorrow.",
  too_many_pending_runs: 'Wait for your earlier runs to finish first.',
  empty_source: 'Write some code first.',
  custom_input_too_large: 'That custom input is too large.',
  csrf_rejected: 'Your session token expired. Reload the page.',
  language_not_offered: 'That course is not offered in this language.',
  placement_in_progress: 'Finish the placement check first.',
  validation_failed: 'Some details are not valid. Check the form and try again.',
  authentication_required: 'Your session ended. Sign in again.',
  codeforces_handle_not_found: "Codeforces doesn't know that handle. Check the spelling.",
  codeforces_invalid_handle: 'Handles are 3–24 letters, digits, dots, dashes or underscores.',
  codeforces_unavailable: "Codeforces isn't answering right now. Try again in a minute.",
  not_linked: 'Link a Codeforces handle first.',
};

export function explain(error: unknown): string {
  if (error instanceof ApiError) return MESSAGES[error.code] ?? `Something went wrong (${error.code}).`;
  return 'Could not reach Socrat. Check your connection and try again.';
}
