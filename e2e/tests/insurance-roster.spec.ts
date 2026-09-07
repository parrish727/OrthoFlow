import { test, expect } from '@playwright/test'

test.describe('Insurance — roster-first UX', () => {
  test.beforeEach(async ({ page }) => {
    // Session is provided by global-setup storageState (no per-test login).
    await page.goto('/insurance')
    await page.waitForLoadState('networkidle')
  })

  test('roster is visible on arrival without searching', async ({ page }) => {
    await expect(page.getByTestId('insurance-page')).toBeVisible()
    const roster = page.getByTestId('insurance-roster')
    await expect(roster).toBeVisible()
    // Multiple patients should be listed immediately (no type-to-see gate).
    const rows = page.locator('[data-testid^="roster-row-"]')
    expect(await rows.count()).toBeGreaterThan(10)
  })

  test('header shows the practice-wide coverage summary', async ({ page }) => {
    await expect(page.getByText(/patients ·/)).toBeVisible()
  })

  test('filter narrows the roster to Priscilla', async ({ page }) => {
    await page.getByTestId('insurance-filter').fill('Priscilla')
    await page.waitForTimeout(400)
    await expect(page.getByText('Knowles, Priscilla')).toBeVisible()
  })

  test('clicking a patient expands their insurance panel', async ({ page }) => {
    await page.getByTestId('insurance-filter').fill('Priscilla')
    await page.waitForTimeout(400)
    const row = page.locator('[data-testid^="roster-row-"]').first()
    await row.click()
    await page.waitForTimeout(800)
    // Panel with plan details + quick links appears (scope to first to avoid the
    // roster-row summary also containing the payer name).
    await expect(page.getByText('Delta Dental of Wisconsin').first()).toBeVisible()
    await expect(page.getByTestId('quicklink-claims')).toBeVisible()
    await expect(page.getByTestId('quicklink-ledger')).toBeVisible()
    await expect(page.getByTestId('quicklink-payments')).toBeVisible()
    await expect(page.getByTestId('quicklink-patient-record')).toBeVisible()
  })

  test('eligibility check returns benefit data', async ({ page }) => {
    await page.getByTestId('insurance-filter').fill('Priscilla')
    await page.waitForTimeout(400)
    await page.locator('[data-testid^="roster-row-"]').first().click()
    await page.waitForTimeout(800)
    const checkBtn = page.locator('[data-testid^="check-eligibility-"]').first()
    await checkBtn.click()
    await page.waitForTimeout(3000)
    await expect(page.locator('[data-testid^="eligibility-result-"]').first()).toBeVisible()
  })

  test('quick-link navigates to the patient ledger', async ({ page }) => {
    await page.getByTestId('insurance-filter').fill('Priscilla')
    await page.waitForTimeout(400)
    await page.locator('[data-testid^="roster-row-"]').first().click()
    await page.waitForTimeout(800)
    await page.getByTestId('quicklink-ledger').click()
    await page.waitForURL(/\/ledger\?patient_id=/)
    expect(page.url()).toContain('/ledger?patient_id=')
  })
})
