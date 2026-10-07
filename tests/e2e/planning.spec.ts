import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

test('diagnostic to reviewed plan, reload, pause, resume, and lighter recovery', async ({ page }, info) => {
  const subject = `m5-e2e-${info.project.name}-${Date.now()}`;
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  execFileSync(python, ['scripts/validation/seed-m4-e2e.py', 'foundations', 'python', subject, '--planning']);
  expect((await page.request.post('/api/v1/auth/dev-login', {
    headers: { Origin: 'http://localhost:3000' }, data: { subject },
  })).ok()).toBe(true);
  await page.goto('/diagnostic');
  await page.getByRole('button', { name: 'Start diagnostic' }).click();
  for (let index = 0; index < 12; index++) {
    if (await page.getByRole('button', { name: 'View diagnostic evidence' }).isVisible()) break;
    await page.getByLabel('2', { exact: true }).check();
    const [saved] = await Promise.all([
      page.waitForResponse(response => response.url().endsWith('/responses') && response.request().method() === 'POST'),
      page.getByRole('button', { name: 'Save answer and continue' }).click(),
    ]);
    expect(saved.ok()).toBe(true);
    const next = await saved.json();
    if (!next.item) break;
    await expect(page.getByText(`${next.answered} answers saved. Item ${next.item.position}.`)).toBeVisible();
  }
  await page.getByRole('button', { name: 'View diagnostic evidence' }).click();
  await page.goto('/plan');
  const panel = page.getByRole('region', { name: 'Learning plan' });
  await panel.getByRole('button', { name: 'Create learning plan' }).click();
  await expect(panel.getByRole('button', { name: 'Confirm reviewed plan' })).toBeEnabled();
  await panel.getByRole('button', { name: 'Confirm reviewed plan' }).click();
  await expect(panel.getByRole('button', { name: 'Pause plan' })).toBeVisible();
  await page.reload();
  await panel.getByRole('button', { name: 'Pause plan' }).click();
  await panel.getByRole('button', { name: 'Resume and review' }).click();
  await expect(panel.getByRole('button', { name: 'Confirm reviewed plan' })).toBeVisible();
  await panel.getByRole('button', { name: 'Review lighter plan' }).click();
  await expect(panel.getByRole('status')).toContainText('20 minutes per planned day');
  await panel.getByRole('button', { name: 'Confirm reviewed plan' }).click();
  await panel.getByRole('button', { name: 'Recalculate after missed days' }).click();
  await expect(panel.getByRole('button', { name: 'Confirm reviewed plan' })).toBeVisible();
});
