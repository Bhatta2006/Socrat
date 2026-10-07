import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

test('independent assessment saves, resumes, finalizes and keeps private keys off the page', async ({ page }, info) => {
  const subject = `m4-e2e-m9-${info.project.name}-${Date.now()}`;
  const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
  execFileSync(python, ['scripts/validation/seed-m4-e2e.py', 'foundations', 'python', subject, '--assessment']);
  expect((await page.request.post('/api/v1/auth/dev-login', {
    headers: { Origin: 'http://localhost:3000' }, data: { subject },
  })).ok()).toBe(true);
  await page.goto('/assessments');
  await page.getByRole('button', { name: 'Start baseline check' }).click();
  await expect(page.getByText('No tutor or solutions.', { exact: false })).toBeVisible();
  expect(await page.locator('body').innerText()).not.toContain('PRIVATE-M9-KEY');
  await page.getByLabel('Your response', { exact: true }).first().fill('PRIVATE-M9-KEY');
  await page.getByRole('button', { name: 'Submit response', exact: true }).first().click();
  await expect(page.getByLabel('Your response', { exact: true })).toHaveCount(1);
  await page.reload();
  await expect(page.getByLabel('Your response', { exact: true })).toHaveCount(1);
  await page.getByLabel('Your response', { exact: true }).fill('PRIVATE-M9-KEY');
  await page.getByRole('button', { name: 'Submit response', exact: true }).click();
  await page.getByRole('button', { name: 'Finish assessment', exact: true }).click();
  await expect(page.getByText('Form passed.', { exact: false })).toBeVisible();
  await page.getByRole('button', { name: 'Start final check' }).click();
  await expect(page.getByText('Synthetic final check 0', { exact: true })).toBeVisible();
});
