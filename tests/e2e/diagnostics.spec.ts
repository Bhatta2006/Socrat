import { expect, test } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import path from 'node:path';

for (const track of ['foundations', 'interview', 'competitive']) {
  for (const language of ['python', 'cpp', 'java']) {
    test(`${track} ${language} diagnostic saves, resumes, and shows limited evidence`, async ({ page }, testInfo) => {
      const subject = `m4-e2e-${track}-${language}-${testInfo.project.name}-${Date.now()}`;
      const python = path.resolve('.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
      execFileSync(python, ['scripts/validation/seed-m4-e2e.py', track, language, subject], { cwd: process.cwd() });
      const login = await page.request.post('/api/v1/auth/dev-login', {
        headers: { Origin: 'http://localhost:3000' }, data: { subject },
      });
      expect(login.ok()).toBe(true);
      await page.goto('/');
      await page.getByRole('button', { name: 'Start diagnostic' }).click();
      await expect(page.getByText('0 answers saved. Item 1.')).toBeVisible();
      await page.getByLabel('2', { exact: true }).check();
      await page.getByRole('button', { name: 'Save answer and continue' }).click();
      await expect(page.getByText('1 answers saved. Item 2.')).toBeVisible();
      await page.reload();
      await expect(page.getByText('1 answers saved. Item 2.')).toBeVisible();
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
      await expect(page.getByTestId('diagnostic-result')).toContainText('Implementation ability has not been verified.');
      await expect(page.getByTestId('diagnostic-result')).toContainText('Limited evidence confidence');
      await page.reload();
      await expect(page.getByTestId('diagnostic-result')).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    });
  }
}
