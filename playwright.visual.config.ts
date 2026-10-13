import { defineConfig, devices } from '@playwright/test';
import base from './playwright.config';

// Screenshot comparisons of key pages, light and dark, desktop (1400 px) and phone (390 px).
// Baselines are per platform because font rendering differs; regenerate with
// `npx playwright test --config playwright.visual.config.ts --update-snapshots`.
const channel = process.env.PW_CHANNEL || undefined;

export default defineConfig({
  ...base,
  testDir: './tests/visual',
  snapshotPathTemplate: '{testDir}/__screenshots__/{platform}/{projectName}/{arg}{ext}',
  expect: { ...base.expect, toHaveScreenshot: { maxDiffPixelRatio: 0.01, animations: 'disabled', caret: 'hide' } },
  projects: [
    { name: 'desktop-light', use: { ...devices['Desktop Chrome'], channel, viewport: { width: 1400, height: 900 }, colorScheme: 'light' } },
    { name: 'desktop-dark', use: { ...devices['Desktop Chrome'], channel, viewport: { width: 1400, height: 900 }, colorScheme: 'dark' } },
    { name: 'phone-light', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium', channel, viewport: { width: 390, height: 844 }, colorScheme: 'light' } },
    { name: 'phone-dark', use: { ...devices['iPhone 13'], defaultBrowserType: 'chromium', channel, viewport: { width: 390, height: 844 }, colorScheme: 'dark' } },
  ],
});
