import { test, expect } from '@playwright/test'

// Phase 4 — Checkout → Work Done → AI creates claim → assign to ledger.
// On the patient's Clinical tab (PatientOrthoPanel), entering a procedure and clicking
// "Work Done" posts the charge to the ledger and drafts an insurance claim (when the patient
// has active insurance). Test profile: Priscilla Knowles.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Checkout → Work Done → claim + ledger', () => {
  test('Work Done posts a charge to the ledger and reports the result', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')

    // PatientOrthoPanel lives on the Clinical tab (default). Enter a procedure.
    await page.getByTestId('charge-cdt').waitFor({ state: 'visible', timeout: 25000 })
    await page.getByTestId('charge-cdt').fill('D8670')
    await page.getByTestId('charge-fee').fill('185')

    // Click Work Done → checkout flow runs.
    await page.getByTestId('work-done').click()

    // A result message confirms the charge posted to the ledger.
    await page.getByTestId('work-done-msg').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('work-done-msg')).toContainText('ledger')
  })
})
