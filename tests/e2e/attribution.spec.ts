import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: {} }));
});

test('attribution page lists sources from the registry and is reachable from the landing footer', async ({ page }) => {
  await page.route('**/api/v1/courses', route => route.fulfill({ json: { items: [] } }));
  await page.goto('/');
  await page.getByRole('navigation', { name: 'Footer' }).getByRole('link', { name: 'Attribution' }).click();
  await expect(page).toHaveURL(/\/attribution$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Attribution' })).toBeVisible();
  // Real registry data from the API: an NC source is link-only, unverified licenses are labelled.
  const usaco = page.getByRole('row', { name: /USACO Guide/ });
  await expect(usaco).toContainText('Linked only; not copied or adapted');
  await expect(page.getByRole('row', { name: /KACTL/ })).toContainText('(unverified)');
  await expect(page.getByText('No lesson, quiz or problem currently adapts third-party text.')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(audit.violations).toEqual([]);
});
