import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';

const scripts = path.resolve('.venv', process.platform === 'win32' ? 'Scripts' : 'bin');
const executable = (name: string) => `"${path.join(scripts, `${name}${process.platform === 'win32' ? '.exe' : ''}`)}"`;
const webPort = Number(process.env.PLAYWRIGHT_WEB_PORT || '3000');
const webOrigin = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  // The browser suite shares one migrated SQLite database across projects.
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: { baseURL: webOrigin, trace: 'retain-on-failure' },
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
        SOCRAT_PUBLIC_ORIGIN: webOrigin,
      },
    },
    { command: `npm run dev --workspace @socrat/web -- --port ${webPort}`, url: webOrigin, reuseExistingServer: !process.env.CI, timeout: 120_000 },
  ],
});
