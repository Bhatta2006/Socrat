import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  const subject = `m10-${crypto.randomUUID()}`;
  await page.route('**/api/v1/auth/dev-login', route => route.continue({ postData: JSON.stringify({ subject }) }));
});

test('learner can control consent and quiet hours, export and request deletion with a receipt', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Enter local workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Today and your progress' })).toBeVisible();
  const controls = page.getByRole('region', { name: 'Accountability and privacy' });
  await controls.getByLabel('I consent to in-app reminders on planned study days.').check();
  await controls.getByLabel('reminder time', { exact: true }).fill('10:00');
  await controls.getByLabel('quiet start', { exact: true }).fill('22:00');
  await controls.getByLabel('quiet end', { exact: true }).fill('08:30');
  await controls.getByLabel('Reminder timezone').fill('Asia/Kolkata');
  await controls.getByLabel('Reduce interface motion').check();
  await controls.getByRole('button', { name: 'Save accountability preferences' }).click();
  await expect(controls.getByRole('status')).toContainText('preferences saved');
  await page.reload();
  await expect(controls.getByLabel('reminder time', { exact: true })).toHaveValue('10:00');
  await expect(controls.getByLabel('Reduce interface motion')).toBeChecked();
  await expect(page.locator('html')).toHaveAttribute('data-reduced-motion', 'true');
  await controls.getByText('Your data and privacy controls', { exact: true }).click();
  const exportDownload = page.waitForEvent('download');
  await controls.getByRole('button', { name: 'Export my learning data' }).click();
  expect((await exportDownload).suggestedFilename()).toBe('socrat-learning-data.json');
  await expect(controls.getByRole('button', { name: 'Request account deletion' })).toBeDisabled();
  await controls.getByLabel('Type DELETE MY DATA to request deletion').fill('DELETE MY DATA');
  await controls.getByRole('button', { name: 'Request account deletion' }).click();
  const receipt = page.getByRole('region', { name: 'Deletion receipt' });
  await expect(receipt).toContainText('Your sessions have been revoked');
  await receipt.getByRole('button', { name: 'Check cleanup status' }).click();
  await expect(receipt).toContainText('queued');
  const receiptDownload = page.waitForEvent('download');
  await receipt.getByRole('button', { name: 'Save deletion receipt' }).click();
  const savedReceipt = await receiptDownload;
  expect(savedReceipt.suggestedFilename()).toBe('socrat-deletion-receipt.json');
  const receiptPath = await savedReceipt.path();
  await page.reload();
  await page.getByText('Check a saved deletion receipt', { exact: true }).click();
  await page.getByLabel('Open your private receipt JSON file').setInputFiles(receiptPath!);
  await expect(page.getByRole('region', { name: 'Deletion receipt' })).toContainText('Your sessions have been revoked');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test('progress uses text bands, discloses uncertainty, separates independent evidence and supports keyboard navigation', async ({ page }, info) => {
  await page.route('**/api/v1/progress*', route => route.fulfill({ json: {
    goal_id: 'synthetic', statement: 'Build a dependable foundation', track: 'foundations', language: 'python',
    target_date: 'no_fixed_date', local_date: '2026-10-07', timezone: 'Asia/Kolkata',
    today: { action: 'rest', minutes: 0 }, plan: null,
    concepts: [{ id: 'loops', title: 'Loops', band: 'developing', confidence: .4, retention_due: true, estimate: .55, reason_codes: ['more_independent_work'] }],
    evidence: [{ id: 'fact', concept_ids: ['loops'], score: .8, mode: 'practice', hint_level: 0, reason_code: 'reviewed', occurred_at: 1 }],
    assessments: [], mastery_changes: [], schedule: [],
    trend: [{ start: '2026-10-01', end: '2026-10-07', independent: { count: 1, solve_rate: 1 }, assisted: { count: 0, solve_rate: null } }],
    uncertainty: 'Confidence depends on independent, varied work and delayed checks; these estimates are not credentials.',
  } }));
  await page.goto('/');
  await page.getByRole('button', { name: 'Enter local workspace' }).click();
  const progress = page.getByRole('region', { name: 'Learning progress' });
  await expect(progress).toContainText('developing · Retention due');
  const disclosure = progress.getByText('Evidence for Loops', { exact: true });
  await disclosure.focus(); await page.keyboard.press('Enter');
  await expect(progress.getByText('Estimate 55%; confidence 40%.')).toBeVisible();
  await progress.getByRole('button', { name: 'Review learning evidence' }).click();
  await expect(progress.getByRole('heading', { name: 'Learning evidence', exact: true })).toBeFocused();
  await expect(progress).toContainText('independent: 1 reviewed attempts');
  await expect(progress).toContainText('assisted: 0 reviewed attempts');
  await page.screenshot({ path: `.cache/m10-progress-${info.project.name}.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
