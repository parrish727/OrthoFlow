import { test, expect } from '@playwright/test'

// Phase 1 — Patient record Clinical Chart vs Administrative split.
// Prime demo patient: Priscilla Knowles.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Patient record — Clinical / Administrative tabs', () => {
  test('both tabs render and switch; clinical is default', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')

    // Tab bar present with both tabs.
    await page.getByTestId('patient-tabs').waitFor({ state: 'attached', timeout: 20000 })
    await expect(page.getByTestId('patient-tab-clinical')).toBeVisible()
    await expect(page.getByTestId('patient-tab-administrative')).toBeVisible()

    // Clinical panel visible by default; administrative hidden.
    await expect(page.getByTestId('patient-clinical-panel')).toBeVisible()
    await expect(page.getByTestId('patient-administrative-panel')).toBeHidden()

    // Switch to Administrative → documents panel shows, clinical hides.
    await page.getByTestId('patient-tab-administrative').click()
    await expect(page.getByTestId('patient-administrative-panel')).toBeVisible()
    await expect(page.getByTestId('patient-documents')).toBeVisible()
    await expect(page.getByTestId('patient-clinical-panel')).toBeHidden()

    // Switch back to Clinical.
    await page.getByTestId('patient-tab-clinical').click()
    await expect(page.getByTestId('patient-clinical-panel')).toBeVisible()
    await expect(page.getByTestId('patient-administrative-panel')).toBeHidden()
  })

  test('administrative tab is self-contained (inline balance/insurance/claims)', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('patient-tab-administrative').click()

    // Inline financial summary is present WITHOUT leaving the tab.
    await page.getByTestId('patient-admin-summary').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('admin-balance-card')).toBeVisible()
    await expect(page.getByTestId('admin-insurance-card')).toBeVisible()
    await expect(page.getByTestId('admin-claims-card')).toBeVisible()
    await expect(page.getByTestId('patient-documents')).toBeVisible()
  })

  test('finance buttons open in-place popups WITHOUT leaving the patient profile', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('patient-tab-administrative').click()
    await page.getByTestId('admin-open-ledger').waitFor({ state: 'visible', timeout: 20000 })

    // Open Ledger as a modal — stays on the patient profile URL (no jump to /ledger).
    await page.getByTestId('admin-open-ledger').click()
    await expect(page.getByTestId('finance-modal')).toBeVisible()
    await expect(page.getByTestId('finance-modal-title')).toHaveText('Ledger')
    await expect(page).toHaveURL(new RegExp(`/patients/${PRISCILLA}`))

    // Close and open Insurance modal in place.
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(page.getByTestId('finance-modal')).toHaveCount(0)
    await page.getByTestId('admin-open-insurance').click()
    await expect(page.getByTestId('finance-modal-title')).toHaveText('Insurance')
    await expect(page).toHaveURL(new RegExp(`/patients/${PRISCILLA}`))

    // Close and open Claims, then Payments — still no navigation away.
    await page.getByRole('button', { name: 'Close' }).click()
    await page.getByTestId('admin-open-claims').click()
    await expect(page.getByTestId('finance-modal-title')).toHaveText('Claims')
    await page.getByRole('button', { name: 'Close' }).click()
    await page.getByTestId('admin-open-payments').click()
    await expect(page.getByTestId('finance-modal-title')).toHaveText('Payments')
    await expect(page).toHaveURL(new RegExp(`/patients/${PRISCILLA}`))

    // Documents still visible underneath in the Administrative tab.
    await page.getByRole('button', { name: 'Close' }).click()
    await expect(page.getByTestId('patient-documents')).toBeVisible()
  })
})
