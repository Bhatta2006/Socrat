// Shared by the runner workers. The digest must match socrat.judge.service.output_digest:
// CRLF/CR become LF, trailing whitespace on each line is dropped, surrounding blank lines too.
export function normalized(text) {
  const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n');
  return lines.map(line => line.trimEnd()).join('\n').replace(/^\n+|\n+$/g, '');
}

export async function digest(text) {
  const bytes = new TextEncoder().encode(normalized(text));
  const hash = await crypto.subtle.digest('SHA-256', bytes);
  return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
}

// Larger outputs are reported as output_limit, like the native runner.
export const OUTPUT_LIMIT = 8_000_000;
// What the page receives back for display; the judge only needs the digest.
export const SHOWN = 16_000;

export async function report(index, status, stdout, stderr, started) {
  const wall_ms = Math.round(performance.now() - started);
  const tooLong = stdout.length > OUTPUT_LIMIT;
  const final = tooLong ? 'output_limit' : status;
  return {
    type: 'case',
    index,
    status: final,
    digest: final === 'executed' ? await digest(stdout) : '',
    wall_ms,
    stdout: stdout.slice(0, SHOWN),
    stderr: stderr.slice(0, SHOWN),
  };
}
