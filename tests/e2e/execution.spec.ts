import { expect, test } from '@playwright/test';

// UI acceptance uses authenticated API-shaped fixtures. It does not attest a live sandbox.
for (const language of ['python', 'cpp', 'java']) {
  test(`CodeMirror ${language}: autosave, resume, contrast, Run and Submit`, async ({ page }) => {
    let source = language === 'java' ? 'public class Solution {}' : '// source';
    let revision = 0;
    let created = false;
    const runs: { id: string; mode: string; status: string; result: unknown }[] = [];
    const draftBodies: { source: string; expected_revision: number }[] = [];
    const runBodies: { stdin: string | null; draft_revision: number }[] = [];
    await page.route('**/api/v1/**', async route => {
      const path = new URL(route.request().url()).pathname;
      const method = route.request().method();
      let json: unknown = { items: [] };
      if (path.endsWith('/features')) json = { onboarding: true, diagnostics: true, code_execution: true };
      else if (path.endsWith('/auth/status')) json = { profile: { id: 'learner', display_name: 'Test', timezone: 'UTC', adult_confirmed: true, csrf_token: 'test' } };
      else if (path.endsWith('/onboarding/goals')) json = { items: [{ id: 'goal', routing_outcome: 'accept_foundations', normalized_statement: 'Synthetic editor test' }] };
      else if (path.endsWith('/diagnostics')) json = { items: [{ id: 'diagnostic', status: 'in_progress', revision: 0, answered: 0, result: null,
        deadline_at: Math.floor(Date.now() / 1000) + 900, active_track: 'foundations', declared_track: 'foundations',
        item: { attempt_id: 'issued', exercise_id: 'exercise', kind: 'implementation', position: 1, choices: [] } }] };
      else if (path.endsWith('/code-attempts') && method === 'GET') json = { items: created ? [{ id: 'attempt', exercise_id: 'exercise', diagnostic_attempt_id: 'issued' }] : [] };
      else if ((path.endsWith('/code-attempts') && method === 'POST') || path.endsWith('/attempts/attempt')) {
        created = true; json = { id: 'attempt', title: 'Double', statement: 'Print twice the input.', language, source, revision, samples: [{ input: '2', expected: '4' }] };
      } else if (path.endsWith('/draft')) {
        const body = route.request().postDataJSON(); draftBodies.push(body);
        expect(body.expected_revision).toBe(revision); source = body.source; revision++;
        json = { saved: true, revision };
      } else if ((path.endsWith('/runs') || path.endsWith('/submit')) && method === 'POST') {
        const body = route.request().postDataJSON(); runBodies.push(body);
        const value = { id: `run-${runs.length}`, mode: path.endsWith('/submit') ? 'submit' : 'run', status: 'completed',
          result: { operational_status: 'healthy', reason_code: 'execution_finalized', cases: [{ index: 0, status: 'passed', wall_ms: 1, stdout: '<script>window.leaked=true</script>', stderr: '' }] } };
        runs.unshift(value); json = value;
      } else if (path.endsWith('/runs')) json = { items: runs };
      await route.fulfill({ json });
    });
    await page.goto('/diagnostic');
    await page.getByRole('button', { name: 'Open code editor' }).click();
    await expect(page.locator('.cm-editor')).toBeVisible();
    await page.getByRole('textbox', { name: 'Solution source code' }).click();
    await page.keyboard.press('ControlOrMeta+A');
    await page.keyboard.press('Enter');
    await page.keyboard.insertText('// autosaved source');
    await page.keyboard.press('Enter');
    await expect.poll(() => draftBodies.length, { timeout: 10000 }).toBe(1);
    expect(source).toBe('\n// autosaved source\n');
    await page.getByLabel('Font size').fill('20');
    await expect(page.locator('.cm-editor')).toHaveCSS('font-size', '20px');
    await expect(page.getByTestId('code-editor')).toHaveAttribute('data-assist-mode', 'assessment');
    await page.getByRole('textbox', { name: 'Solution source code' }).focus();
    await page.keyboard.press('Control+Space');
    await expect(page.locator('.cm-tooltip-autocomplete')).toHaveCount(0);
    await page.keyboard.press('Escape'); await page.keyboard.press('Tab');
    await expect(page.getByRole('textbox', { name: 'Solution source code' })).not.toBeFocused();
    await page.getByLabel('Editor contrast').selectOption('high-contrast');
    await expect(page.getByTestId('code-editor')).toHaveAttribute('data-editor-theme', 'high-contrast');
    await page.getByLabel('Custom input').fill(' 3\n');
    await page.getByRole('button', { name: 'Run custom input' }).click();
    await expect.poll(() => runBodies.length).toBe(1);
    expect(runBodies[0]).toMatchObject({ stdin: ' 3\n', draft_revision: 1 });
    await expect(page.getByText('<script>window.leaked=true</script>', { exact: true })).toBeVisible();
    expect(await page.evaluate(() => (window as unknown as { leaked?: boolean }).leaked)).toBeUndefined();
    await page.getByRole('button', { name: 'Run samples' }).click();
    await page.getByRole('button', { name: 'Submit independent attempt' }).click();
    await expect.poll(() => runBodies.length).toBe(3);
    expect(runBodies[2]).toMatchObject({ stdin: null, draft_revision: 1 });
    await expect(page.getByRole('textbox', { name: 'Solution source code' })).toHaveAttribute('contenteditable', 'false');
    await page.reload();
    await page.getByRole('button', { name: 'Open code editor' }).click();
    await expect(page.locator('.cm-editor')).toBeVisible();
    await expect(page.getByRole('textbox', { name: 'Solution source code' })).toHaveText(source.trim());
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  });
}
