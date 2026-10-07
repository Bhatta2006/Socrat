import { chromium } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'node:fs';
const browser = await chromium.launch();
const measurements = [];
for (let n = 0; n < 3; n++) {
  const context = await browser.newContext();
  const page = await context.newPage();
  const scripts = [];
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', async response => {
    if (response.request().resourceType() === 'script') {
      try { scripts.push({ url: response.url(), bytes: (await response.body()).length }); } catch {}
    }
  });
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    let json = { items: [] };
    if (path.endsWith('/features')) json = { code_execution: true, diagnostics: true, onboarding: true };
    else if (path.endsWith('/auth/status')) json = { profile: { id: 'learner', display_name: 'Test', timezone: 'UTC', adult_confirmed: true, csrf_token: 'test' } };
    else if (path.endsWith('/onboarding/goals')) json = { items: [{ id: 'goal', active_track: 'foundations', goal: { language: 'python' }, normalized_statement: 'Editor measurement' }] };
    else if (path.endsWith('/diagnostics')) json = { items: [{ id: 'diagnostic', status: 'in_progress', answered: 0, declared_track: 'foundations', active_track: 'foundations', deadline_at: 2000000000, item: { kind: 'implementation', attempt_id: 'issued', exercise_id: 'exercise' } }] };
    else if (path.endsWith('/code-attempts') && route.request().method() === 'POST') json = { id: 'attempt', title: 'Double', statement: 'Print twice the input.', mode: 'diagnostic', language: 'python', source: 'print(4)', revision: 0, samples: [{ input: '2', expected: '4' }] };
    await route.fulfill({ json });
  });
  const started = performance.now();
  await page.goto('http://127.0.0.1:3100/diagnostic');
  await page.getByRole('button', { name: 'Open code editor' }).click().catch(async e => { console.log(await page.locator('body').innerText(), errors); throw e; });
  await page.getByRole('textbox', { name: 'Solution source code' }).waitFor();
  const readyMs = performance.now() - started;
  await page.waitForTimeout(300);
  measurements.push({ readyMs: Math.round(readyMs), jsBytes: scripts.reduce((n,x) => n+x.bytes,0), scripts, errors });
  await context.close();
}
await browser.close();
mkdirSync('.cache', { recursive: true });
writeFileSync(`.cache/editor-${process.argv[2] ?? 'measurement'}.json`, JSON.stringify(measurements,null,2));
console.log(JSON.stringify(measurements.map(({readyMs,jsBytes,errors})=>({readyMs,jsBytes,errors}))));
