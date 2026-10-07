import { expect, test } from '@playwright/test';

test('beginner reviews and saves an honest waitlist goal on desktop and mobile', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Enter local workspace' }).click();
  await page.goto('/onboarding');
  await page.getByLabel('Display name').fill('Beginner');
  await page.getByLabel('Timezone', { exact: true }).fill('Asia/Kolkata');
  await page.getByLabel('I confirm I am 18 or older.').check();
  await page.getByRole('button', { name: 'Save profile' }).click();
  await page.getByRole('button', { name: 'Continue to your learning goal' }).click();
  await page.getByLabel('Goal', { exact: true }).selectOption('interview');
  await page.getByRole('button', { name: 'Next', exact:true }).click();
  await page.getByRole('button', { name: 'Next', exact:true }).click();
  await page.getByLabel('I have no fixed target date.').check();
  await page.getByRole('button', { name: 'Review goal', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Review your goal' })).toBeVisible();
  await expect(page.getByText('Content for this goal and language is not available yet.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Confirm goal' })).toBeDisabled();
  await page.getByLabel('I reviewed this goal and starting route.').check();
  await page.getByRole('button', { name: 'Confirm goal' }).click();
  await expect(page.getByTestId('saved-goal')).toContainText('Goal saved on the waitlist');
  await page.reload();
  await page.getByRole('button', { name: 'Continue to your learning goal' }).click();
  await expect(page.getByTestId('saved-goal')).toContainText('new grad');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
