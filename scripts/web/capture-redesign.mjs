// Captures representative pages at 390, 768 and 1440 px in light and dark for the redesign record.
// Usage (with the demo running on :3000): node scripts/web/capture-redesign.mjs docs/redesign/after
import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import path from 'node:path';

const out = path.resolve(process.argv[2] || 'docs/redesign/after');
const base = 'http://localhost:3000';
const widths = { phone: [390, 844], tablet: [768, 1024], desktop: [1440, 900] };
const pages = [
  ['landing', '/'],
  ['login', '/login'],
  ['today', '/today'],
  ['skills', '/plan'],
  ['lesson', '/learn/zero/programs-and-output'],
  ['quiz', '/quiz/quiz/zero/programs-and-output'],
  ['problem', '/problems/greeting'],
  ['problems', '/library'],
  ['companies', '/companies'],
  ['sprint', '/sprint'],
  ['assessment', '/assessments'],
  ['playground', '/playground'],
  ['evidence', '/progress'],
  ['settings', '/settings'],
];

async function learner(context) {
  const request = context.request;
  const headers = { Origin: base };
  const login = await request.post(`${base}/api/v1/auth/dev-login`, { headers, data: { subject: `capture-${Date.now()}`, display_name: 'Maya' } });
  if (!login.ok()) throw new Error(`dev login failed: ${login.status()}`);
  const profile = await (await request.get(`${base}/api/v1/me`)).json();
  const write = { ...headers, 'X-CSRF-Token': profile.csrf_token };
  await request.patch(`${base}/api/v1/me`, { headers: write, data: { birth_year: 2000, timezone: 'Asia/Kolkata' } });
  await request.post(`${base}/api/v1/enrollments`, { headers: write, data: { course: 'zero', language: 'python', level: 'brand-new', minutes_per_day: 45, weekdays: [0, 1, 2, 3, 4, 5, 6] } });
}

async function settle(page) {
  await page.waitForLoadState('networkidle').catch(() => undefined);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(500);
}

// Optional filters for spot checks: ONLY=today,skills SCHEMES=dark WIDTHS=phone,desktop
const only = process.env.ONLY ? process.env.ONLY.split(',') : null;
const schemes = process.env.SCHEMES ? process.env.SCHEMES.split(',') : ['dark', 'light'];
const devices = process.env.WIDTHS ? process.env.WIDTHS.split(',') : Object.keys(widths);

const browser = await chromium.launch({ channel: process.env.PW_CHANNEL || undefined });
try {
  for (const scheme of schemes) {
    for (const [device, [width, height]] of Object.entries(widths).filter(([d]) => devices.includes(d))) {
      // Public pages first, signed out; then the learner's pages.
      const publicContext = await browser.newContext({ viewport: { width, height }, colorScheme: scheme, reducedMotion: 'reduce' });
      const signedIn = await browser.newContext({ viewport: { width, height }, colorScheme: scheme, reducedMotion: 'reduce' });
      await learner(signedIn);
      for (const [name, route] of pages.filter(([n]) => !only || only.includes(n))) {
        const context = name === 'landing' || name === 'login' ? publicContext : signedIn;
        const page = await context.newPage();
        await page.goto(base + route);
        await settle(page);
        const dir = path.join(out, scheme, device);
        mkdirSync(dir, { recursive: true });
        await page.screenshot({ path: path.join(dir, `${name}.jpg`), fullPage: true, type: 'jpeg', quality: 60 });
        await page.close();
        process.stdout.write(`${scheme}/${device}/${name} `);
      }
      await publicContext.close();
      await signedIn.close();
    }
  }
} finally {
  await browser.close();
}
console.log(`\nSaved to ${out}`);
