import { expect, test } from '@playwright/test';

test('local learner can sign in, persist profile, reload and sign out', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/login');
  await expect(page.getByRole('heading', { name: 'Welcome to Socrat' })).toBeVisible();
  await page.getByRole('button', { name: 'Enter local workspace' }).click();
  await page.goto('/settings');
  await expect(page.getByRole('heading', { name: 'Your profile' })).toBeVisible();
  await page.getByLabel('Display name').fill('Ada Lovelace');
  await page.getByLabel('Timezone', { exact: true }).fill('Asia/Kolkata');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByRole('status')).toContainText('Profile saved');
  await page.reload();
  await expect(page.getByLabel('Display name')).toHaveValue('Ada Lovelace');
  await expect(page.getByLabel('Timezone', { exact: true })).toHaveValue('Asia/Kolkata');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.locator('.user-menu summary').click();
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page.getByRole('button', { name: 'Enter local workspace' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('invalid timezone is explained without losing the entered name', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Enter local workspace' }).click();
  await page.goto('/settings');
  await page.getByLabel('Display name').fill('Grace');
  await page.getByLabel('Timezone', { exact: true }).fill('Mars/City');
  await page.getByRole('button', { name: 'Save profile' }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'IANA timezone' })).toBeVisible();
  await expect(page.getByLabel('Display name')).toHaveValue('Grace');
});
