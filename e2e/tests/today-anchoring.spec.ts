import { test, expect } from '@playwright/test'

// Regression guard: "today" must be anchored to the practice timezone (America/New_York), not
// UTC. The Playwright container runs in UTC; before the fix, the Schedule defaulted to the UTC
// date (which after 8 PM ET is tomorrow) and showed an empty board even though today's demo data
// exists. This asserts the default schedule view renders today's appointments.
test.describe('Today anchoring (practice timezone)', () => {
  test('Schedule default view shows today\'s appointments', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')
    // At least one appointment card must render for the default (today) date.
    await page.locator('[data-testid^="appt-patient-"]').first().waitFor({ state: 'visible', timeout: 25000 })
    expect(await page.locator('[data-testid^="appt-patient-"]').count()).toBeGreaterThan(0)
  })
})
