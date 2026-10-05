import { expect, test } from '@playwright/test';

// UI-shaped fixtures exercise timer/reload/editor handoff; Python tests enforce real broker admission.
for (const variant of [false, true]) test(`timed window survives reload and saves source before ${variant ? 'a repair variant' : 'upsolve'}`, async ({ page }) => {
  let serverNow = Math.floor(Date.now() / 1000);
  let deadline: number | undefined;
  let revision = 0;
  let phase = 'independent';
  let source = '# initial source\n';
  let repairSource = '';
  let draftRevision = 0;
  let repairRevision = 0;
  let completed = false;
  const commands: Record<string, unknown>[] = [];
  const sessionView = () => ({ id: 'session', revision, status: completed ? 'completed' : 'in_progress',
    local_date: '2026-10-05', track: 'competitive', language: 'python', planned_minutes: 6, upsolve_reserved_minutes: 1,
    timing: 'standard', ...(phase === 'independent' ? { server_now: serverNow } : {}),
    blocks: [
      { mode: phase, title: variant && phase === 'upsolve' ? 'Repair task' : 'Double', minutes: phase === 'upsolve' ? 1 : 5, modality: 'code', timed: phase === 'independent',
        status: completed ? 'submitted' : 'available', exercise_ids: [variant && phase === 'upsolve' ? 'repair-exercise' : 'exercise'],
        attempt_id: phase === 'upsolve' ? 'repair' : 'parent',
        ...(deadline === undefined ? {} : { deadline_at: deadline }),
        ...(phase === 'upsolve' ? { error_classification: variant ? 'concept_gap' : 'time_pressure', repair_selection: variant ? 'concept_matched_variant' : 'saved_solution', timed_outcome: { outcome: 'timed_out' } } : {}),
        content: { prompt: 'Print twice the input.', explanations: [], examples: [] } },
    ],
  });
  await page.route('**/api/v1/**', async route => {
    const pathname = new URL(route.request().url()).pathname;
    let json: unknown = { items: [] };
    if (pathname.endsWith('/features')) json = { onboarding: true, diagnostics: true, planning: true, learning_sessions: true, code_execution: true };
    else if (pathname.endsWith('/me')) json = { id: 'learner', display_name: 'Test', timezone: 'UTC', adult_confirmed: true, csrf_token: 'csrf' };
    else if (pathname.endsWith('/onboarding/goals')) json = { items: [{ id: 'goal', routing_outcome: 'accept_competitive', normalized_statement: 'Synthetic timed practice' }] };
    else if (pathname.endsWith('/diagnostics')) json = { items: [{ id: 'diagnostic', item: null,
      active_track: 'competitive', declared_track: 'competitive', scope: 'objective_readiness',
      status: 'completed', answered: 4, revision: 4, server_time: serverNow, deadline_at: serverNow + 900,
      result: {
      concepts: {}, missing_evidence: [], placement_sufficient: true, full_placement: true },
    }] };
    else if (pathname.endsWith('/curriculum')) json = { revision: 1, status: 'confirmed', feasibility: 'on_track',
      start_date: '2026-10-05', feasible_target_date: '2026-11-05', provisional: false, reason_codes: [],
      weekly_reserve_minutes: 5, assessment_reservation_minutes: 3, controller: { workload_minutes: 30 },
      schedule: { minutes: 30, weekdays: [0, 2, 4], target_date: 'no_fixed_date' }, nodes: [], days: [],
    };
    else if (pathname.endsWith('/learning-session')) json = { session: sessionView() };
    else if (pathname.endsWith('/commands')) {
      const body = route.request().postDataJSON(); commands.push(body);
      expect(body.expected_revision).toBe(revision);
      if (body.action === 'start_timed') { deadline = serverNow + 300; }
      else if (body.action === 'upsolve') {
        expect(body.error_classification).toBe(variant ? 'concept_gap' : 'time_pressure');
        expect(source).toBe('# last unsaved edit before upsolve\n');
        repairSource = variant ? '# repair starter\n' : source; phase = 'upsolve';
      }
      revision++; json = sessionView();
    } else if (pathname.endsWith('/draft')) {
      const body = route.request().postDataJSON();
      if (pathname.includes('/parent/')) {
        expect(body.expected_revision).toBe(draftRevision); source = body.source; draftRevision++;
        json = { saved: true, revision: draftRevision };
      } else {
        expect(body.expected_revision).toBe(repairRevision); repairSource = body.source; repairRevision++;
        json = { saved: true, revision: repairRevision };
      }
    } else if (pathname.endsWith('/attempts/parent') || pathname.endsWith('/attempts/repair')) {
      const repair = pathname.endsWith('/repair');
      json = { id: repair ? 'repair' : 'parent', title: 'Double', statement: 'Print twice the input.', language: 'python',
        source: repair ? repairSource : source, revision: repair ? repairRevision : draftRevision, samples: [{ input: '2', expected: '4' }] };
    }
    await route.fulfill({ json });
  });
  await page.clock.install();
  await page.goto('/');
  const today = page.getByRole('region', { name: 'Today’s learning session' });
  await expect(today.getByText('Includes 1 minutes reserved for optional upsolve.', { exact: false })).toBeVisible();
  await today.getByRole('button', { name: 'Start timed practice' }).click();
  await expect(today.getByRole('button', { name: 'Pause session' })).toBeDisabled();
  await page.reload();
  await expect(today.getByRole('button', { name: 'Start timed practice' })).toHaveCount(0);
  await today.getByRole('button', { name: 'Open code editor' }).click();
  await expect(page.locator('.monaco-editor')).toBeVisible();
  serverNow += 301;
  await page.clock.fastForward(301_000);
  await expect(today.getByText('Timed window ended. Your code is saved.', { exact: true })).toBeVisible();
  await expect(today.getByRole('button', { name: 'Submit independent attempt' })).toBeDisabled();
  await page.evaluate(() => {
    const win = window as unknown as { monaco: { editor: { getModels: () => { setValue: (value: string) => void }[] } } };
    win.monaco.editor.getModels()[0].setValue('# last unsaved edit before upsolve\n');
  });
  if (variant) await today.getByLabel('What should you repair?').selectOption('concept_gap');
  await today.getByRole('button', { name: 'Start upsolve' }).click();
  await expect(today.getByRole('heading', { name: variant ? 'upsolve: Repair task' : 'upsolve: Double' })).toBeVisible();
  expect(repairSource).toBe(variant ? '# repair starter\n' : '# last unsaved edit before upsolve\n');
  if (variant) await expect(today.getByText('Your original solution stays saved.', { exact: false })).toBeVisible();
  await today.getByRole('button', { name: 'Open code editor' }).click();
  await expect(page.locator('.monaco-editor')).toBeVisible();
  await expect(today.getByRole('button', { name: 'Submit independent attempt' })).toBeEnabled();
  expect(commands.map(body => body.action)).toEqual(['start_timed', 'upsolve']);
});
