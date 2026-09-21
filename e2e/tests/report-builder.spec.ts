import { test, expect } from '@playwright/test'

// Phase 6 — Customizable Reports builder + flagship "didn't pay → bundle message".
test.describe('Report Builder + bundle message', () => {
  test('run a filtered patient report and bundle-message the result set', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')

    // Open the Report Builder tab.
    await page.getByTestId('reports-tab-builder').click()
    await page.getByTestId('report-builder').waitFor({ state: 'visible', timeout: 20000 })

    // Filter to patients who owe money, run the report.
    await page.getByTestId('filter-payment').selectOption('owes')
    await page.getByTestId('run-report').click()
    await page.getByTestId('report-results').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.locator('[data-testid="report-row"]').first()).toBeVisible()

    // Flagship action: bundle-message everyone who didn't pay.
    await page.getByTestId('bundle-message-open').click()
    await page.getByTestId('bundle-modal').waitFor({ state: 'visible' })
    await page.getByTestId('bundle-body').fill('Friendly reminder: you have a balance on your account.')
    await page.getByTestId('bundle-send').click()

    // Confirmation of queued messages.
    await page.getByTestId('bundle-result').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('bundle-result')).toContainText('Queued')
  })

  test('insurance tab returns insured patients with remaining benefit', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('reports-tab-builder').click()
    await page.getByTestId('builder-tab-insurance').click()
    await page.getByTestId('run-report').click()
    await page.getByTestId('report-results').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.locator('[data-testid="report-row"]').first()).toBeVisible()
  })
})
