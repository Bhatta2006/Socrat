import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

function grantRole(userId: string, role: string) {
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  const script = 'import sqlite3,sys; db=sqlite3.connect(sys.argv[1]); db.execute("INSERT INTO content_operators (user_id, role) VALUES (?, ?)", (sys.argv[2], sys.argv[3])); db.commit(); db.close()';
  execFileSync(python, ['-c', script, path.resolve('socrat.e2e.db'), userId, role]);
}

async function signInAs(page: import('@playwright/test').Page, subject: string, role: string) {
  const origin = new URL(page.url()).origin;
  const login = await page.request.post('/api/v1/auth/dev-login', {
    headers: { Origin: origin }, data: { subject },
  });
  expect(login.ok()).toBe(true);
  const me = await page.request.get('/api/v1/me');
  expect(me.ok()).toBe(true);
  grantRole((await me.json()).id, role);
}

test('content operator can inspect and import a draft manifest', async ({ page }) => {
  const submitted: unknown[] = [];
  const versions: Array<{ id: string; key: string; version: string; status: string; is_active: boolean; digest: string }> = [];
  const manifest = {
    contract_version: 1, release_stage: 'draft', key: 'argument-reasoning', version: '0.1.0',
    name: 'Argument reasoning', domain: 'critical-thinking', content: [],
  };
  await page.route('**/api/v1/me', route => route.fulfill({ json: { id: 'operator', csrf_token: 'csrf' } }));
  await page.route('**/api/v1/admin/content-roles', route => route.fulfill({ json: { roles: ['author'] } }));
  await page.route('**/api/v1/admin/skill-packs**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/skill-packs') && route.request().method() === 'GET') {
      await route.fulfill({ json: versions });
    } else if (url.pathname.endsWith('/skill-packs') && route.request().method() === 'POST') {
      submitted.push(route.request().postDataJSON());
      versions.push({ id: 'pack-1', key: manifest.key, version: manifest.version, status: 'draft', is_active: false, digest: 'sha256' });
      await route.fulfill({ status: 201, json: { id: 'pack-1', status: 'draft', digest: 'sha256' } });
    } else {
      await route.fulfill({ json: { id: 'pack-1', status: 'draft', digest: 'sha256', manifest, required_reviews: ['domain_reviewer'], reviews: [] } });
    }
  });

  await page.goto('/admin/skill-packs');
  await expect(page.getByRole('heading', { name: 'Skill-pack operations' })).toBeVisible();
  await page.getByLabel('Manifest JSON').fill(JSON.stringify(manifest));
  await page.getByRole('button', { name: 'Import draft' }).click();
  await expect(page.getByRole('button', { name: 'argument-reasoning 0.1.0' })).toBeVisible();
  await expect(page.getByText('Draft versions are not available to learners.')).toBeVisible();
  expect(submitted).toEqual([manifest]);
});

test('non-operator cannot access inventory or release controls', async ({ page }) => {
  await page.route('**/api/v1/me', route => route.fulfill({ json: { id: 'learner', csrf_token: 'csrf' } }));
  await page.route('**/api/v1/admin/content-roles', route => route.fulfill({ json: { roles: [] } }));
  await page.goto('/admin/skill-packs');
  await expect(page.getByText('Content role required')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Import draft' })).toHaveCount(0);
});

test('release owner can publish a reviewed candidate and quarantine it', async ({ page }) => {
  let status = 'draft';
  const actions: Array<{ path: string; csrf: string; body: unknown }> = [];
  const manifest = {
    key: 'logic', version: '1.0.0', name: 'Logic', release_stage: 'candidate',
    concepts: [{ key: 'premises' }], content: [{ key: 'premise-lesson', kind: 'lesson' }],
  };
  await page.route('**/api/v1/me', route => route.fulfill({ json: { id: 'release-owner', csrf_token: 'csrf' } }));
  await page.route('**/api/v1/admin/content-roles', route => route.fulfill({ json: { roles: ['release_owner'] } }));
  await page.route('**/api/v1/admin/skill-packs**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (route.request().method() === 'POST') {
      actions.push({ path, csrf: route.request().headers()['x-csrf-token'], body: route.request().postDataJSON() });
      status = path.endsWith('/publish') ? 'released' : 'quarantined';
      await route.fulfill({ json: { status } });
    } else if (path.endsWith('/skill-packs')) {
      await route.fulfill({ json: [{ id: 'pack-1', key: 'logic', version: '1.0.0', status, is_active: status === 'released', digest: 'sha256' }] });
    } else {
      await route.fulfill({ json: {
        id: 'pack-1', status, digest: 'sha256', manifest,
        required_reviews: ['domain_reviewer'],
        reviews: [{ role: 'domain_reviewer', decision: 'approve', note: 'Reviewed contract', reviewer_id: 'reviewer' }],
      } });
    }
  });

  await page.goto('/admin/skill-packs');
  await page.getByRole('button', { name: 'logic 1.0.0' }).click();
  await page.getByRole('button', { name: 'Publish version' }).click();
  await expect(page.getByRole('status')).toContainText('Version published.');
  await page.getByLabel('Quarantine reason').fill('Incorrect explanation found');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Quarantine pack' }).click();
  await expect(page.getByRole('status')).toContainText('Pack quarantined.');
  expect(actions).toEqual([
    { path: '/api/v1/admin/skill-packs/pack-1/publish', csrf: 'csrf', body: null },
    { path: '/api/v1/admin/skill-packs/pack-1/quarantine', csrf: 'csrf', body: { reason: 'Incorrect explanation found' } },
  ]);
});

test('named operators complete import, review, publish, and quarantine against the real API', async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto('/');
  const fixture = JSON.parse(readFileSync(path.resolve('contracts/skill-packs/non-dsa-fixture.json'), 'utf8'));
  const key = `browser-fixture-${randomUUID().slice(0, 8)}`;
  fixture.key = key;
  fixture.release_stage = 'candidate';
  fixture.coverage[0].status = 'released';
  const evidence = { uri: 'fixture://release-check', sha256: '0'.repeat(64), summary: 'Synthetic browser test evidence only' };
  fixture.release_evidence = {
    rights: evidence, accessibility: evidence, concept_quality: evidence,
    exercise_quality: evidence, assessment_separation: evidence, canary: evidence,
  };
  fixture.content = [{
    key: 'premise-lesson', kind: 'lesson', concept_keys: ['premises'], evidence_modes: ['explain'],
    language_variants: [], title: 'Identify a premise',
    source: { author: 'Socrat test', license: 'original', rights_checked_at: '2026-09-30' },
    accessibility_notes: 'Plain text response',
  }];
  await signInAs(page, `author-${randomUUID().slice(0, 8)}`, 'author');
  await page.goto('/admin/skill-packs');
  await page.getByLabel('Manifest JSON').fill(JSON.stringify(fixture));
  await page.getByRole('button', { name: 'Import draft' }).click();
  await expect(page.getByRole('status')).toContainText('Manifest imported as a draft version.');

  for (const role of [
    'domain_reviewer', 'learning_reviewer', 'accessibility_reviewer',
    'rights_reviewer', 'assessment_reviewer',
  ]) {
    await signInAs(page, `reviewer-${randomUUID().slice(0, 8)}`, role);
    await page.goto('/admin/skill-packs');
    await page.getByRole('button', { name: `${key} 0.1.0` }).click();
    await page.getByLabel('Review role').selectOption(role);
    await page.getByLabel('Review note').fill(`Reviewed ${role} fixture contract`);
    await page.getByRole('button', { name: 'Record review' }).click();
    await expect(page.getByRole('status')).toContainText('Review recorded.');
  }

  await signInAs(page, `release-${randomUUID().slice(0, 8)}`, 'release_owner');
  await page.goto('/admin/skill-packs');
  await page.getByRole('button', { name: `${key} 0.1.0` }).click();
  await page.getByRole('button', { name: 'Publish version' }).click();
  await expect(page.getByRole('status')).toContainText('Version published.');
  const published = await page.request.get('/api/v1/skill-packs');
  expect((await published.json()).some((pack: { key: string }) => pack.key === key)).toBe(true);

  await page.getByLabel('Quarantine reason').fill('Fixture release retired after verification');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: 'Quarantine pack' }).click();
  await expect(page.getByRole('status')).toContainText('Pack quarantined.');
  const afterQuarantine = await page.request.get('/api/v1/skill-packs');
  expect((await afterQuarantine.json()).some((pack: { key: string }) => pack.key === key)).toBe(false);
});
