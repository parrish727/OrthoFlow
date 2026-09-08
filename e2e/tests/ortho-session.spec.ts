import { test, expect } from '@playwright/test'

// Session from global-setup storageState.

test.describe('Reports — categories', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')
  })

  test('category cards are visible and run a report', async ({ page }) => {
    await expect(page.getByTestId('reports-categories')).toBeVisible()
    // Several category cards render
    expect(await page.locator('[data-testid^="report-cat-"]').count()).toBeGreaterThan(5)
    // Run "patients who owe money"
    await page.getByTestId('report-cat-patients_owe').click()
    await expect(page.getByTestId('category-report-result')).toBeVisible({ timeout: 15000 })
  })

  test('treatment overdue shows AI suggestions', async ({ page }) => {
    await page.getByTestId('report-cat-treatment_overdue').click()
    await expect(page.getByTestId('category-report-result')).toBeVisible({ timeout: 15000 })
    await expect(page.getByText(/✨/).first()).toBeVisible()
  })
})

test.describe('Schedule — Medicaid MC + owe indicator', () => {
  test('schedule renders appointment cards', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1500)
    // At least one appointment card with a patient testid
    const cards = page.locator('[data-testid^="appt-patient-"]')
    expect(await cards.count()).toBeGreaterThan(0)
  })
})

test.describe('Patient ortho panel — comments + chart charges', () => {
  test('ortho panel renders with comments + chart charge sections', async ({ page }) => {
    // Navigate to a patient via Insurance roster (fast path to a real patient id)
    await page.goto('/insurance')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('insurance-filter').fill('Priscilla')
    await page.waitForTimeout(500)
    await page.locator('[data-testid^="roster-row-"]').first().click()
    await page.waitForTimeout(600)
    await page.getByTestId('quicklink-patient-record').click()
    await page.waitForURL(/\/patients\//)
    await page.waitForTimeout(2500)

    // Panel + both comment charts + the charge inputs are present (feature wired & reachable).
    await expect(page.getByTestId('patient-ortho-panel')).toBeVisible()
    await expect(page.getByTestId('comments-tab-info')).toBeVisible()
    await expect(page.getByTestId('comments-tab-clinical')).toBeVisible()
    await expect(page.getByTestId('comment-input')).toBeVisible()
    await expect(page.getByTestId('charge-cdt')).toBeVisible()
    await expect(page.getByTestId('charge-add')).toBeVisible()
  })
})
