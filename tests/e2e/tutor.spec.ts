import { expect, test } from '@playwright/test';

// Browser fixtures test the real workspace/tutor components; API tests enforce policy.
test('practice hints save code, survive reload, and label assisted submissions', async ({ page }) => {
  let source = '# learner source';
  let revision = 0;
  const hints: Record<string, unknown>[] = [];
  const requests: Record<string, unknown>[] = [];
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const method = route.request().method();
    let json: unknown = { items: [] };
    if (path.endsWith('/features')) json = { onboarding: true, diagnostics: true, planning: true, code_execution: true, tutor: true };
    else if (path.endsWith('/me')) json = { id: 'learner', display_name: 'Test', timezone: 'UTC', adult_confirmed: true, csrf_token: 'test' };
    else if (path.endsWith('/onboarding/goals')) json = { items: [{ id: 'goal', routing_outcome: 'accept_foundations', normalized_statement: 'Tutor fixture' }] };
    else if (path.endsWith('/diagnostics')) json = { items: [{ id: 'diagnostic', item: null, active_track: 'foundations', declared_track: 'foundations',
      scope: 'objective_readiness', status: 'completed', answered: 4, revision: 4, result: { concepts: {}, missing_evidence: [], placement_sufficient: true, full_placement: true } }] };
    else if (path.endsWith('/curriculum')) json = { revision: 1, status: 'confirmed', feasibility: 'on_track',
      start_date: '2026-10-06', feasible_target_date: '2026-11-06', reason_codes: [], nodes: [],
      controller: { workload_minutes: 30 }, weekly_reserve_minutes: 5, assessment_reservation_minutes: 3,
      schedule: { minutes: 30, weekdays: [0, 2, 4], target_date: 'no_fixed_date' },
      days: [{ date: '2026-10-06', status: 'available', capacity_minutes: 30, deferred_reviews: [],
        blocks: [{ mode: 'independent', minutes: 5, title: 'Double', timed: false, modality: 'code', exercise_ids: ['exercise'] }] }] };
    else if (path.endsWith('/code-attempts') && method === 'GET') json = { items: [{ id: 'attempt', exercise_id: 'exercise', diagnostic_attempt_id: null }] };
    else if (path.endsWith('/attempts/attempt')) json = { id: 'attempt', title: 'Double', statement: 'Print twice the input.', language: 'python', source, revision,
      samples: [{ input: '2', expected: '4' }], mode: 'practice', assistance_level: hints.length ? 1 : 0 };
    else if (path.endsWith('/draft')) {
      const body = route.request().postDataJSON(); expect(body.expected_revision).toBe(revision);
      source = body.source; revision++; json = { saved: true, revision };
    } else if (path.endsWith('/tutor') && method === 'GET') json = { items: hints, assistance_level: hints.length ? 1 : 0 };
    else if (path.endsWith('/tutor')) {
      const body = route.request().postDataJSON(); requests.push(body);
      expect(body.draft_revision).toBe(revision); expect(source).toBe('# saved before the hint');
      const hint = { id: `hint-${hints.length}`, granted_level: body.action === 'exit' ? 5 : 1,
        fallback: true, review_required: false, fresh_task_required: body.action === 'exit',
        response: { diagnosis: '', message: '<script>window.tutorLeak=true</script>', question: 'What result do you expect?' } };
      hints.push(hint); json = hint;
    }
    await route.fulfill({ json });
  });
  await page.goto('/');
  await page.getByRole('button', { name: 'Open code editor' }).click();
  await expect(page.locator('.monaco-editor')).toBeVisible();
  const tutor = page.getByRole('region', { name: 'Practice tutor' });
  await expect(tutor.getByRole('button', { name: 'Ask for a hint' })).toBeDisabled();
  await page.evaluate(() => {
    const win = window as unknown as { monaco: { editor: { getModels: () => { setValue: (s: string) => void }[] } } };
    win.monaco.editor.getModels()[0].setValue('# saved before the hint');
  });
  await tutor.getByLabel('Your plan and what you tried').fill('I will trace the sample first.');
  await tutor.getByRole('button', { name: 'Ask for a hint' }).click();
  await expect(tutor.getByText('What result do you expect?')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Submit assisted attempt' })).toBeVisible();
  expect(requests).toHaveLength(1);
  expect(await page.evaluate(() => (window as Window & { tutorLeak?: boolean }).tutorLeak)).toBeUndefined();
  await page.reload();
  await page.getByRole('button', { name: 'Open code editor' }).click();
  await expect(tutor.getByText('What result do you expect?')).toBeVisible();
  await tutor.getByLabel('Your plan and what you tried').fill('I want to study the explanation.');
  await tutor.getByRole('button', { name: 'End independent attempt and show explanation' }).click();
  await expect(tutor.getByText('This is now learning-only.', { exact: false })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
