import http from 'node:http';
import { timingSafeEqual } from 'node:crypto';
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// The secret may be mounted as a file (SOCRAT_EXPLAINER_CHECKER_SECRET_FILE) so it never sits in the environment.
const secretFile = process.env.SOCRAT_EXPLAINER_CHECKER_SECRET_FILE;
const token = (secretFile ? readFileSync(secretFile, 'utf8').trim() : process.env.SOCRAT_EXPLAINER_CHECKER_SECRET || '');
if (token.length < 32) throw Error('Configure a strong checker secret');
const script = fileURLToPath(new URL('./check-artifact.mjs', import.meta.url));
let running = 0;
const server = http.createServer(async (request, response) => {
  const reply = (status, data) => { response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); response.end(JSON.stringify(data)); };
  if (request.url === '/health' && request.method === 'GET') return reply(200, { ok: true });
  const supplied = Buffer.from((request.headers.authorization || '').replace(/^Bearer /, ''));
  const expected = Buffer.from(token);
  if (request.url !== '/check' || request.method !== 'POST' || supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) return reply(403, { error: 'forbidden' });
  if (running >= 2) return reply(429, { error: 'busy' });
  running++;
  try {
    let raw = '';
    for await (const chunk of request) { raw += chunk; if (raw.length > 700_000) return reply(413, { error: 'too_large' }); }
    JSON.parse(raw);
    const child = spawn(process.execPath, [script], {
      cwd: path.resolve(path.dirname(script), '../..'), detached: process.platform !== 'win32',
      env: Object.fromEntries(Object.entries(process.env).filter(([key]) => ['PATH','HOME','TMPDIR','TEMP','TMP','SYSTEMROOT','SYSTEMDRIVE','WINDIR','LOCALAPPDATA','PROGRAMFILES','PROGRAMFILES(X86)','PROGRAMW6432','PLAYWRIGHT_BROWSERS_PATH','SOCRAT_EXPLAINER_BROWSER_CHANNEL'].includes(key.toUpperCase()))),
      stdio: ['pipe','pipe','ignore'],
    });
    const result = await new Promise(resolve => {
      let output = '', done = false;
      const finish = value => { if (!done) { done=true;clearTimeout(timer);resolve(value); } };
      const timer = setTimeout(() => {
        try { if (process.platform !== 'win32') process.kill(-child.pid, 'SIGKILL'); else child.kill(); } catch {}
        finish({ ok: false, reason: 'Visual exceeded the browser time budget' });
      }, 18_000);
      child.stdout.on('data', data => { output += data; if (output.length > 128_000) { child.kill();finish({ ok:false,reason:'Invalid checker output' }); } });
      child.on('error', () => finish({ ok:false,reason:'Browser checker unavailable' }));
      child.on('close', () => { try {finish(JSON.parse(output));} catch {finish({ok:false,reason:'Browser check did not complete'});} });
      child.stdin.on('error', () => {}); child.stdin.end(raw);
    });
    reply(200, result);
  } catch { reply(400, { error: 'invalid_request' }); }
  finally { running--; }
});
server.listen(Number(process.env.PORT || 8010), '0.0.0.0', () => console.log(JSON.stringify({ port: server.address().port })));
