import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

for (const track of ['foundations', 'interview', 'competitive']) for (const language of ['python', 'cpp', 'java']) {
  test(`${track} ${language} lesson checks keep private keys and saved history`, async ({ page }, info) => {
    const subject = `m5-e2e-m7-content-${track}-${info.project.name}-${Date.now()}`;
    const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
    execFileSync(python, ['scripts/validation/seed-m4-e2e.py', track, language, subject, '--planning', '--learning-content']);
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
    const commands = `/api/v1/goals/${goalId}/curriculum/commands`;
    const weekdayName = new Intl.DateTimeFormat('en', { timeZone: 'Asia/Kolkata', weekday: 'short' }).format(new Date());
    const weekday = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].indexOf(weekdayName);
    const weekdays = [weekday, (weekday + 2) % 7, (weekday + 4) % 7].sort();
    const generated = await page.request.post(commands, { headers,
      data: { action: 'generate', expected_revision: 0, idempotency_key: 'generate', weekdays },
    });
    expect(generated.ok(), await generated.text()).toBe(true);
    const draft = await generated.json();
    expect((await page.request.post(commands, { headers,
      data: { action: 'confirm', expected_revision: draft.revision, reviewed_digest: draft.review_digest, idempotency_key: 'confirm' },
    })).ok()).toBe(true);
    const before = await (await page.request.get('/api/v1/learner-state/evidence')).json();
    await page.goto('/session/today');
    const today = page.getByRole('region', { name: 'Today’s learning session' });
    await today.getByRole('button', { name: 'Start today’s session' }).click();
    await expect(today.getByRole('heading', { level: 4 })).toBeFocused();
    await today.getByLabel('Your response').focus();
    await today.getByLabel('Your response').press('4');
    await expect(today.getByLabel('Your response')).toHaveValue('four');
    await today.getByLabel('Your response').press('Tab');
    await expect(today.getByRole('button', { name: 'Save and continue' })).toBeFocused();
    await today.getByRole('button', { name: 'Save and continue' }).press('Enter');
    await expect(today.getByText('retrieval check: Review this concept.', { exact: false })).toBeVisible();
    await expect(today.getByText(`Synthetic ${language} semantics note.`, { exact: true })).toBeVisible();
    await expect(today.getByRole('heading', { level: 4 })).toBeFocused();
    if (track === 'interview') await expect(today.getByText('Synthetic loop invariant.', { exact: true })).toBeVisible();
    await today.getByRole('button', { name: 'Save and continue' }).click();
    await expect(today.getByRole('heading', { level: 4 })).toContainText('guided');
    await expect(today.getByRole('heading', { level: 4 })).toBeFocused();
    await today.getByLabel('Your response').fill('<script>window.sessionLeak=true</script> saved trace');
    await today.getByRole('button', { name: 'Save and continue' }).click();
    await expect(today.getByRole('heading', { level: 4 })).toContainText('independent');
    await today.getByLabel('Your response').fill('independent text remains ungraded');
    await today.getByRole('button', { name: 'Save and continue' }).click();
    await expect(today.getByRole('heading', { level: 4 })).toContainText('exit check');
    await today.getByLabel('Your response').fill('4');
    await today.getByRole('button', { name: 'Save and continue' }).click();
    await expect(today.getByText('exit check: Correct.', { exact: false })).toBeVisible();
    await page.reload();
    await today.getByRole('button', { name: 'View past sessions' }).click();
    await today.getByRole('button', { name: /\d{4}-\d{2}-\d{2} · completed/ }).click();
    const saved = today.getByRole('region', { name: 'Saved learning session' });
    await expect(saved.getByText('Saved response: <script>window.sessionLeak=true</script> saved trace', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => (window as Window & { sessionLeak?: boolean }).sessionLeak)).toBeUndefined();
    const after = await (await page.request.get('/api/v1/learner-state/evidence')).json();
    expect(after.total).toBe(before.total);
    const telemetry = await (await page.request.get(`/api/v1/goals/${goalId}/learning-session-telemetry`)).json();
    expect(telemetry.meaningful_sessions).toBe(0);
    expect(telemetry.activation.activated).toBe(false);
  });
}
