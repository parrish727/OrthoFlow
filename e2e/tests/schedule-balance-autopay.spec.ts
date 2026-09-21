import { test, expect } from '@playwright/test'

// Task #10 — Schedule money-symbol balance popup + Ledger auto-pay color coding.
// Session comes from global-setup storageState (no per-test login).

test.describe('Schedule — money-symbol balance popup', () => {
  test('clicking the $ badge on an owing patient opens a balance popup', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')

    // Wait for appointment cards to render (schedule is data-heavy).
    await page.locator('[data-testid^="appt-patient-"]').first().waitFor({ state: 'visible', timeout: 25000 })

    // Find the first owes-money badge ($). Seeded data has patients with balances.
    const owesBadge = page.locator('[data-testid^="owes-badge-"]').first()
    await owesBadge.waitFor({ state: 'visible', timeout: 25000 })

    // Derive the appointment id from the badge testid so we can target its popup.
    const testid = await owesBadge.getAttribute('data-testid')
    const apptId = (testid || '').replace('owes-badge-', '')

    await owesBadge.click()

    // Popup appears with a balance amount.
    const popup = page.getByTestId(`balance-popup-${apptId}`)
    await expect(popup).toBeVisible({ timeout: 15000 })
    await expect(page.getByTestId(`balance-popup-amount-${apptId}`)).toBeVisible()
    await expect(popup).toContainText('Balance')

    // Close it.
    await page.getByTestId(`balance-popup-close-${apptId}`).click()
    await expect(popup).toHaveCount(0)
  })
})

test.describe('Ledger — auto-pay color coding', () => {
  const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

  test('auto-pay ledger entries render GREEN (resolved) and RED (failed)', async ({ page }) => {
    // Deep-link straight to Priscilla's ledger (auto-expands via patient_id query param).
    await page.goto(`/ledger?patient_id=${PRISCILLA}`)
    await page.waitForLoadState('networkidle')

    // Wait for the expanded transaction rows to load.
    await page.locator('[data-testid^="ledger-entry-"]').first().waitFor({ state: 'visible', timeout: 25000 })

    // At least one resolved (GREEN) auto-pay badge.
    const resolved = page.locator('[data-testid^="autopay-resolved-"]')
    await expect(resolved.first()).toBeVisible({ timeout: 15000 })
    expect(await resolved.count()).toBeGreaterThan(0)

    // Exactly the seeded failed (RED) auto-pay badge.
    const failed = page.locator('[data-testid^="autopay-failed-"]')
    await expect(failed.first()).toBeVisible({ timeout: 15000 })
    await expect(failed.first()).toContainText('AUTO-PAY FAILED')
  })
})
