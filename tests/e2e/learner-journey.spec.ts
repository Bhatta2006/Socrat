import { expect, test, type Page } from '@playwright/test';

/** One learner's first session through the v2 web app, on desktop and mobile. */

async function signIn(page: Page, name: string) {
  await page.goto('/login');
  await page.getByLabel('Your name').fill(name);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page).toHaveURL(/\/start$/);
}

async function onboard(page: Page, course: RegExp, level: RegExp) {
  await page.getByLabel('What should we call you?').fill('Ada');
  await page.getByLabel('Year you were born').selectOption('2001');
  await page.getByRole('button', { name: 'Continue' }).click();
  await page.getByRole('button', { name: course }).click();
  await page.getByRole('button', { name: level }).click();
  await page.getByRole('button', { name: 'Python', exact: true }).click();
  await page.getByRole('button', { name: '45 min' }).click();
  await page.getByRole('button', { name: 'Build my plan' }).click();
}

test('a beginner reads a lesson, passes its check and sees progress', async ({ page }, info) => {
  await signIn(page, `beginner-${info.project.name}-${Date.now()}`);
  await onboard(page, /Programming from Zero/, /never written code/);

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Ada');
  await expect(page.getByRole('heading', { name: 'Programs and output' })).toBeVisible();
  await page.getByRole('link', { name: 'Start lesson' }).click();

  await expect(page).toHaveURL(/\/learn\/zero\/programs-and-output$/);
  // Only the learner's language variant of each code sample is shown.
  await expect(page.locator('pre[data-lang="python"]').first()).toBeVisible();
  await expect(page.locator('pre[data-lang="cpp"], pre[data-lang="java"]')).toHaveCount(0);
  await page.getByRole('button', { name: 'Mark lesson complete' }).click();
  await page.getByRole('link', { name: 'Take the concept check' }).click();

  await expect(page).toHaveURL(/\/quiz\/quiz\/zero\/programs-and-output$/);
  for (;;) {
    const results = page.getByRole('link', { name: 'Continue' });
    if (await results.isVisible()) break;
    await page.getByRole('radio').first().click();
    await page.getByRole('button', { name: 'Check answer' }).click();
    await expect(page.getByRole('status').filter({ hasText: /Correct|Not quite/ })).toBeVisible();
    await page.getByRole('button', { name: /Next question|See results/ }).click();
  }
  await expect(page.getByText(/of \d+ correct/)).toBeVisible();
  await page.getByRole('link', { name: 'Continue' }).click();

  await expect(page).toHaveURL(/\/today$/);
  await expect(page.getByText('Programs and output check')).toBeVisible();
  await page.goto('/progress');
  await expect(page.getByRole('heading', { name: 'Mastery by concept' })).toBeVisible();
  await page.goto('/plan');
  await expect(page.getByRole('heading', { name: 'Roadmap' })).toBeVisible();
});

test('placement adapts, then practice and the Socratic tutor work', async ({ page }, info) => {
  test.setTimeout(180_000); // the tutor may call a live model
  await signIn(page, `placed-${info.project.name}-${Date.now()}`);
  await onboard(page, /DSA for Interviews/, /know the basics of one language/);

  await expect(page).toHaveURL(/\/placement$/);
  const ready = page.getByRole('heading', { name: 'Your plan is ready' });
  const counter = page.getByText(/^Question \d+ of at most \d+$/);
  for (let asked = 0; asked < 25; asked++) {
    await expect(counter.or(ready)).toBeVisible();
    if (await ready.isVisible()) break;
    const before = await counter.textContent();
    await page.getByRole('button', { name: "I don't know yet" }).click();
    await expect(ready.or(counter.filter({ hasNotText: before ?? '' }))).toBeVisible();
  }
  await page.getByRole('link', { name: "Go to today's plan" }).click();
  await expect(page).toHaveURL(/\/today$/);

  await page.goto('/problems/sum-of-multiples');
  await expect(page.getByRole('heading', { name: 'Sum of multiples' })).toBeVisible();
  await expect(page.getByTestId('code-editor')).toBeVisible();
  await expect(page.getByText('Draft saved')).toBeVisible();

  await page.getByRole('button', { name: 'Stuck? Ask for a hint' }).click();
  const tutor = page.getByRole('dialog', { name: 'Socratic tutor' });
  await expect(tutor).toBeVisible();
  await tutor.getByRole('button', { name: 'Give me a hint' }).click();
  // A live model (when one is configured) takes longer than the curated offline reply.
  await expect(tutor.locator('.chat-bubble-assistant').last()).toHaveText(/\w/, { timeout: 90_000 });
  await expect(tutor.getByRole('button', { name: 'Show solution' })).toBeEnabled({ timeout: 90_000 });
  await tutor.getByRole('button', { name: 'Show solution' }).click();
  await tutor.getByRole('button', { name: 'Yes, show it' }).click();
  // Without real attempts the server withholds the full answer.
  await expect(tutor.locator('.chat-bubble-assistant').last()).toContainText('To unlock the full walkthrough');
  await page.keyboard.press('Escape');
  await expect(tutor).toBeHidden();

  await page.goto('/settings');
  await page.getByRole('button', { name: '20 min' }).click();
  await page.getByRole('button', { name: 'Save changes' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toBeVisible();
  await page.goto('/plan');
  await expect(page.getByText(/You updated your plan: 20 min per study day/)).toBeVisible();
});

test('the practice library filters, saves and never shows raw links', async ({ page }, info) => {
  await signIn(page, `library-${info.project.name}-${Date.now()}`);
  await onboard(page, /Competitive Programming/, /never written code|new to programming/);
  await expect(page).toHaveURL(/\/(today|placement)$/);

  await page.goto('/today');
  await expect(page.getByRole('heading', { name: 'Practice picked for you' })).toBeVisible();
  await page.goto('/library?platform=Codeforces&rating_min=1200&rating_max=1300&sort=easiest');
  await expect(page.getByRole('heading', { name: 'Practice library' })).toBeVisible();
  const rows = page.locator('tbody tr');
  await expect(rows.first()).toContainText('Codeforces');
  await expect(rows.first()).toContainText('1200');
  // Names link out to the official site; addresses are never printed.
  expect(await page.locator('main').innerText()).not.toMatch(/https?:\/\//);
  const title = (await rows.first().getByRole('link').first().innerText()).replace(/\s*↗.*$/s, '');

  await rows.first().getByRole('button', { name: 'Save to my list' }).click();
  await expect(rows.first().getByRole('button', { name: 'Remove from my list' })).toBeVisible();
  await rows.first().getByRole('button', { name: /Mark as solved|✓/ }).first().click();
  await page.getByRole('tab', { name: 'My list' }).click();
  await expect(rows).toHaveCount(1);
  await expect(rows.first()).toContainText(title);
  await expect(rows.first().getByRole('button', { name: /Solved/ })).toBeVisible();
});
