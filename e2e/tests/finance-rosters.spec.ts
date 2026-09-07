import { test, expect } from '@playwright/test'

// Session provided by global-setup storageState (no per-test login).

test.describe('Claims — roster-first UX', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/claims')
    await page.waitForLoadState('networkidle')
  })

  test('roster of patients-with-claims is visible on arrival', async ({ page }) => {
    await expect(page.getByTestId('claims-page')).toBeVisible()
    await expect(page.getByTestId('claims-roster')).toBeVisible()
    expect(await page.locator('[data-testid^="claims-row-"]').count()).toBeGreaterThan(5)
  })

  test('clicking a patient expands their claims + quick-links', async ({ page }) => {
    await page.locator('[data-testid^="claims-row-"]').first().click()
    await page.waitForTimeout(800)
    await expect(page.getByTestId('quicklink-insurance')).toBeVisible()
    await expect(page.getByTestId('quicklink-ledger')).toBeVisible()
    await expect(page.getByTestId('quicklink-payments')).toBeVisible()
  })

  test('filter narrows the roster', async ({ page }) => {
    await page.getByTestId('claims-filter').fill('Knowles')
    await page.waitForTimeout(400)
    const rows = page.locator('[data-testid^="claims-row-"]')
    expect(await rows.count()).toBeLessThan(10)
  })
})

test.describe('Ledger — roster-first UX', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/ledger')
    await page.waitForLoadState('networkidle')
  })

  test('roster of patient balances visible on arrival', async ({ page }) => {
    await expect(page.getByTestId('ledger-page')).toBeVisible()
    await expect(page.getByTestId('ledger-roster')).toBeVisible()
    expect(await page.locator('[data-testid^="ledger-row-"]').count()).toBeGreaterThan(5)
  })

  test('clicking a patient shows transactions + quick-links', async ({ page }) => {
    await page.locator('[data-testid^="ledger-row-"]').first().click()
    await page.waitForTimeout(800)
    await expect(page.getByTestId('quicklink-insurance').first()).toBeVisible()
    await expect(page.getByTestId('quicklink-claims').first()).toBeVisible()
  })

  test('quick-link navigates to that patient insurance', async ({ page }) => {
    await page.locator('[data-testid^="ledger-row-"]').first().click()
    await page.waitForTimeout(800)
    await page.getByTestId('quicklink-insurance').first().click()
    await page.waitForURL(/\/insurance\?patient_id=/)
    expect(page.url()).toContain('/insurance?patient_id=')
  })
})

test.describe('Payments — roster-first UX', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/payments')
    await page.waitForLoadState('networkidle')
  })

  test('roster of patients-with-payments visible on arrival', async ({ page }) => {
    await expect(page.getByTestId('payments-page')).toBeVisible()
    await expect(page.getByTestId('payments-roster')).toBeVisible()
    expect(await page.locator('[data-testid^="payments-row-"]').count()).toBeGreaterThan(3)
  })

  test('clicking a patient shows payment history + quick-links', async ({ page }) => {
    await page.locator('[data-testid^="payments-row-"]').first().click()
    await page.waitForTimeout(800)
    await expect(page.getByTestId('quicklink-ledger')).toBeVisible()
    await expect(page.getByTestId('quicklink-claims')).toBeVisible()
  })
})
