import { test, expect } from '@playwright/test'
import { loginAsPatient } from '../fixtures/auth'

// Wave 3 — appointment confirmation + MyOrthoChart sync + virtual visit + cancellation feed.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Wave 3 — schedule confirm / portal sync / notifications', () => {
  test('Schedule card exposes a Confirm control and confirmation checkmark', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')
    // At least one appointment card renders a Confirm button OR an already-confirmed checkmark.
    const confirmBtns = page.locator('[data-testid^="appt-confirm-"]')
    const confirmedMarks = page.locator('[data-testid^="appt-confirmed-"]')
    await expect
      .poll(async () => (await confirmBtns.count()) + (await confirmedMarks.count()), { timeout: 20000 })
      .toBeGreaterThan(0)
  })

  test('MyOrthoChart shows a notifications feed + confirm/cancel on upcoming visits', async ({ page }) => {
    await loginAsPatient(page)
    await page.goto('/portal')
    await page.waitForLoadState('networkidle')
    // Notifications nav → feed section renders.
    await page.getByRole('button', { name: /Notifications/ }).click()
    await page.getByTestId('portal-notifications').waitFor({ state: 'visible', timeout: 20000 })
    // Visits section has confirm/cancel controls for upcoming appts.
    await page.getByRole('button', { name: /^Visits$/ }).click()
    const anyConfirm = page.locator('[data-testid^="portal-confirm-"]')
    const anyCancel = page.locator('[data-testid^="portal-cancel-"]')
    await expect
      .poll(async () => (await anyConfirm.count()) + (await anyCancel.count()), { timeout: 20000 })
      .toBeGreaterThan(0)
  })
})
