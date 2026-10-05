import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

test('Today saves normal-session blocks, resumes after reload, and keeps text ungraded', async ({ page }, info) => {
  const subject = `m5-e2e-m7-${info.project.name}-${Date.now()}`;
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  execFileSync(python, ['scripts/validation/seed-m4-e2e.py', 'foundations', 'python', subject, '--planning']);
  expect((await page.request.post('/api/v1/auth/dev-login', {
    headers: { Origin: 'http://localhost:3000' }, data: { subject },
  })).ok()).toBe(true);
  const me = await (await page.request.get('/api/v1/me')).json();
  const headers = { Origin: 'http://localhost:3000', 'X-CSRF-Token': me.csrf_token };
  const goals = await (await page.request.get('/api/v1/onboarding/goals')).json();
  const goalId = goals.items[0].id;
  let diagnostic = await (await page.request.post(`/api/v1/goals/${goalId}/diagnostics`, { headers })).json();
  while (diagnostic.item) {
    const response = await page.request.post(`/api/v1/diagnostics/${diagnostic.id}/responses`, {
      headers, data: { attempt_id: diagnostic.item.attempt_id, revision: diagnostic.revision,
        idempotency_key: diagnostic.item.attempt_id, answer: 'two' },
    });
    expect(response.ok()).toBe(true); diagnostic = await response.json();
  }
  expect((await page.request.post(`/api/v1/diagnostics/${diagnostic.id}/complete`, { headers })).ok()).toBe(true);
  const weekdayName = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Kolkata', weekday: 'short' }).format(new Date());
  const weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(weekdayName);
  const weekdays = [weekday, (weekday + 2) % 7, (weekday + 4) % 7].sort();
  const commands = `/api/v1/goals/${goalId}/curriculum/commands`;
  const draftResponse = await page.request.post(commands, { headers,
    data: { action: 'generate', expected_revision: 0, idempotency_key: 'generate', weekdays },
  });
  expect(draftResponse.ok()).toBe(true);
  const draft = await draftResponse.json();
  expect((await page.request.post(commands, { headers,
    data: { action: 'confirm', expected_revision: draft.revision, reviewed_digest: draft.review_digest, idempotency_key: 'confirm' },
  })).ok()).toBe(true);
  const before = await (await page.request.get('/api/v1/learner-state/evidence')).json();
  await page.goto('/');
  const today = page.getByRole('region', { name: 'Today’s learning session' });
  await today.getByRole('button', { name: 'Start today’s session' }).click();
  await expect(today.getByRole('status')).toContainText('in progress');
  await today.getByLabel('Your response').fill('<script>window.sessionLeak=true</script> recalled state');
  await today.getByRole('button', { name: 'Save and continue' }).click();
  await expect(today.getByRole('heading', { level: 4 })).toContainText('instruction');
  await today.getByRole('button', { name: 'Pause session' }).click();
  await page.reload();
  await expect(today.getByRole('status')).toContainText('paused');
  await today.getByRole('button', { name: 'Resume session' }).click();
  await today.getByRole('button', { name: 'Save and continue' }).click();
  for (const mode of ['guided', 'independent', 'exit check']) {
    await expect(today.getByRole('heading', { level: 4 })).toContainText(mode);
    await today.getByLabel('Your response').fill(`My ${mode} response`);
    if (mode === 'exit check') await today.getByLabel('What made this task difficult?').selectOption('concept_gap');
    await today.getByRole('button', { name: 'Save and continue' }).click();
  }
  await expect(today.getByRole('status')).toContainText('completed');
  await page.reload();
  await expect(today.getByRole('status')).toContainText('completed');
  expect(await page.evaluate(() => (window as Window & { sessionLeak?: boolean }).sessionLeak)).toBeUndefined();
  const after = await (await page.request.get('/api/v1/learner-state/evidence')).json();
  expect(after.total).toBe(before.total);
});
