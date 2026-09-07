// Global setup: authenticate once as owner and persist the session so every test reuses it.
// This removes per-test login latency (a source of flakiness when the API is behind a CDN).
import { chromium, FullConfig } from '@playwright/test'

const OWNER_EMAIL = 'demo@orthoflowsolutions.com'
const PASSWORD = 'Demo2026!'

export default async function globalSetup(config: FullConfig) {
  const baseURL = process.env.E2E_BASE_URL || config.projects[0]?.use?.baseURL || 'http://orthoflow-frontend-1:3000'
  const browser = await chromium.launch()
  const page = await browser.newPage({ baseURL })
  await page.goto('/login')
  await page.locator('input[type="email"]').fill(OWNER_EMAIL)
  await page.locator('input[type="password"]').fill(PASSWORD)
  await Promise.all([
    page.waitForResponse(r => r.url().includes('/auth/login') && r.request().method() === 'POST', { timeout: 40000 }),
    page.getByRole('button', { name: /sign in|log in/i }).click(),
  ])
  await page.waitForFunction(() => !!localStorage.getItem('token'), { timeout: 20000 })
  await page.context().storageState({ path: 'storage/owner.json' })
  await browser.close()
}
