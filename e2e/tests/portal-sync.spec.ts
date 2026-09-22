import { test, expect, Page } from '@playwright/test'
import { loginAsPatient } from '../fixtures/auth'

// MyOrthoChart sync — the patient portal reflects OrthoFlow connections:
// live billing (balance + auto-pay status mirroring the ledger color coding) and a Documents section.
async function openMenuAndGo(page: Page, label: RegExp) {
  await page.getByRole('button', { name: /menu/i }).click()
  await page.getByRole('button', { name: label }).click()
}

test.describe('MyOrthoChart — sync with OrthoFlow features', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsPatient(page)
  })

  test('Billing shows live balance and auto-pay status on payments', async ({ page }) => {
    await openMenuAndGo(page, /^billing$/i)
    await page.getByTestId('portal-billing').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('portal-balance')).toBeVisible()
    await expect(page.getByTestId('portal-recent-payments')).toBeVisible({ timeout: 15000 })
    // Priscilla has a seeded declined auto-pay → a failed chip renders.
    await expect(page.getByTestId('portal-autopay-failed').first()).toBeVisible({ timeout: 15000 })
  })

  test('Documents section is available in the portal', async ({ page }) => {
    await openMenuAndGo(page, /^documents$/i)
    await page.getByTestId('portal-documents').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible()
  })
})
