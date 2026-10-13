import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/auth/status', route => route.fulfill({ json: { profile: null } }));
  await page.route('**/api/v1/features', route => route.fulfill({ json: {} }));
  await page.route('**/api/v1/courses', route => route.fulfill({ json: { items: [{ id: 'zero', title: 'Programming from Zero', concept_count: 18, problem_count: 25 }] } }));
});

test('landing example, course links and questions work on desktop and phone', async ({ page }, info) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Think deeper.Code better.');
  await expect(page.getByRole('link', { name: 'Start learning', exact: true })).toHaveAttribute('href', '/login');
  await expect(page.locator('.path-count')).toHaveText('18 concepts · 25 judged problems');
  await page.getByRole('button', { name: 'Java', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Java', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('.workspace-code pre')).toContainText('int[] findPair');
  await page.getByRole('button', { name: 'Show me a hint' }).click();
  await expect(page.locator('#example-hint')).toBeVisible();
  await expect(page.locator('#example-hint')).toContainText('1 + 7 = 8');
  await page.getByRole('button', { name: 'Hide the hint' }).click();
  await expect(page.locator('#example-hint')).toBeHidden();
  await page.getByText('Can I start without knowing how to code?', { exact: true }).click();
  await expect(page.locator('.landing-question').first()).toHaveAttribute('open', '');
  await expect(page.getByRole('link', { name: /Get started with/ })).toHaveCount(3);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  const nav = await page.locator('.landing-nav').boundingBox();
  expect(nav?.y).toBe(12);
  expect(nav?.height).toBeLessThan(65);
  if (info.project.name === 'mobile') {
    await page.getByRole('button', { name: 'Open navigation' }).click();
    await expect(page.getByRole('navigation', { name: 'Mobile site' })).toBeVisible();
    await page.getByRole('button', { name: 'Close navigation' }).press('Escape');
    await expect(page.getByRole('navigation', { name: 'Mobile site' })).toHaveCount(0);
  }
  const audit = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa', 'wcag21aa']).analyze();
  expect(audit.violations).toEqual([]);
});

test('ribbons approach the viewer on scroll and motion preferences are respected', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto('/');
  const ribbon = page.locator('.ribbon-stage');
  const scale = () => ribbon.evaluate(element => new DOMMatrix(getComputedStyle(element).transform).m11);
  await expect.poll(() => ribbon.getAttribute('style')).toContain('transform:');
  const before = await scale();
  await page.evaluate(() => window.scrollTo(0, 400));
  await expect.poll(scale).toBeGreaterThan(before + 0.1);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await expect.poll(async () => (await page.locator('.landing-nav').boundingBox())?.y).toBe(12);
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await expect.poll(scale).toBe(1);
});

test('landing remains usable without WebGL or the course API', async ({ page }) => {
  await page.addInitScript(() => {
    const context = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (kind: string, ...args: unknown[]) {
      if (kind === 'webgl') return null;
      return context.apply(this, [kind, ...args] as Parameters<typeof context>);
    } as typeof context;
  });
  await page.route('**/api/v1/courses', route => route.fulfill({ status: 503, json: { error: { code: 'unavailable' } } }));
  await page.goto('/');
  await expect(page.locator('.ribbon-fallback')).toBeVisible();
  await expect(page.getByRole('link', { name: /Get started with/ })).toHaveCount(3);
  await expect(page.locator('.path-count')).toHaveCount(0);
  await page.getByRole('link', { name: 'Start learning', exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});
