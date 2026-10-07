import { defineConfig, devices } from '@playwright/test';

// The demo suite never starts an API, injects state, or mocks execution.
// Run against a fresh stack started by npm run dev:demo.
export default defineConfig({
  testDir: './tests/e2e',
  testMatch: 'demo-walkthrough.spec.ts',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 240_000,
  expect: { timeout: 30_000 },
  outputDir: 'docs/demo/screens/videos',
  reporter: [['list'], ['json', { outputFile: '.cache/demo-walkthrough-results.json' }]],
  use: {
    baseURL: 'http://localhost:3000',
    actionTimeout: 30000,
    navigationTimeout: 60000,
    video: 'on',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium', deviceScaleFactor: 1, viewport: { width: 390, height: 844 } } },
  ],
});
