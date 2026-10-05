import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const scripts = path.resolve('.venv', process.platform === 'win32' ? 'Scripts' : 'bin');
const executable = (name: string) => `"${path.join(scripts, `${name}${process.platform === 'win32' ? '.exe' : ''}`)}"`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: { baseURL: 'http://localhost:3000', trace: 'retain-on-failure' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium' } },
  ],
  webServer: [
    {
      command: `${executable('alembic')} upgrade head && ${executable('uvicorn')} socrat.main:create_app --factory --app-dir services/api/src --host 127.0.0.1 --port 8000`,
      url: 'http://127.0.0.1:8000/api/health/ready',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        SOCRAT_DATABASE_URL: 'sqlite:///socrat.e2e.db',
        SOCRAT_DEV_LOGIN_ENABLED: 'true',
        SOCRAT_ONBOARDING_ENABLED: 'true',
        SOCRAT_DIAGNOSTICS_ENABLED: 'true',
        SOCRAT_PLANNING_ENABLED: 'true',
        SOCRAT_LEARNING_SESSIONS_ENABLED: 'true',
        SOCRAT_PUBLIC_ORIGIN: 'http://localhost:3000',
      },
    },
    { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: !process.env.CI, timeout: 120_000 },
  ],
});
