// Playwright config for the Docker-based runner (official mcr.microsoft.com/playwright image).
// Runs on the docker_agent-net network and targets the frontend container directly, which
// avoids host browser-launch issues. The app itself calls api.orthoflowsolutions.com over
// the internet, so no API proxying is needed.
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 45000,
  retries: 1,
  globalSetup: './global-setup.ts',
  reporter: [['line'], ['html', { open: 'never', outputFolder: 'playwright-report' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://orthoflow-frontend-1:3000',
    storageState: 'storage/owner.json',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    // In-container browsers; no webServer needed (targets the live app).
  },
  webServer: undefined,
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
})
