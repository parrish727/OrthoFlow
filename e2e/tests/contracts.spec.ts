import { test, expect } from '@playwright/test'

// Phase 3 — Contracts section: create → verify insurance → place (connects to ledger) → EOD report.
// Test profile: Priscilla Knowles.
const PRISCILLA_NAME = 'Priscilla Knowles'

test.describe('Contracts (TC → Contracts → lifecycle)', () => {
  test('create a contract for Priscilla, verify insurance, and place it', async ({ page }) => {
    await page.goto('/contracts')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('contracts-page').waitFor({ state: 'visible', timeout: 20000 })

    // Create a private-pay contract (auto-verifiable) for Priscilla.
    await page.getByTestId('new-contract').click()
    await page.getByTestId('create-contract-modal').waitFor({ state: 'visible' })
    // Select Priscilla by visible label in the patient dropdown.
    await page.getByTestId('contract-patient').selectOption({ label: PRISCILLA_NAME })
    // Set payer to private so verification is immediate, and add first charges + down payment.
    await page.getByTestId('contract-payer').selectOption('private')
    await page.getByTestId('save-contract').click()

    // New contract row appears.
    await page.getByTestId('contracts-list').waitFor({ state: 'visible', timeout: 20000 })
    const row = page.locator('[data-testid^="contract-row-"]').first()
    await expect(row).toBeVisible()

    // Verify insurance then place (buttons are per-row).
    const verifyBtn = row.locator('[data-testid^="verify-"]')
    if (await verifyBtn.count()) await verifyBtn.click()
    const placeBtn = row.locator('[data-testid^="place-"]')
    await placeBtn.first().click()

    // After placing, the row shows the active status pill.
    await expect(row.getByText('active', { exact: true })).toBeVisible({ timeout: 20000 })
  })

  test('EOD report opens and shows the day summary', async ({ page }) => {
    await page.goto('/contracts')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('open-eod').click()
    await page.getByTestId('eod-modal').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByText('End-of-Day Report')).toBeVisible()
    await expect(page.getByText('Appointments')).toBeVisible()
    await expect(page.getByText('Financials')).toBeVisible()
  })
})
