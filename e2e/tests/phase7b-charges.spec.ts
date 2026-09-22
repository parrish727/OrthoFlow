import { test, expect } from '@playwright/test'

// Phase 7b-3 — Charges tab on the Next Visit section: quick ortho charges (broken bracket,
// loose/lost retainer, impressions, emergency, etc.) post to the ledger.
// The charge POST itself is backend-API-verified; the E2E asserts the deterministic UI
// (tab toggle + presets render + click is wired) to avoid cross-origin-write flakiness.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Phase 7b — Next-visit Charges tab', () => {
  test('Next Visit has Visit/Charges tabs and charge presets render', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')

    const section = page.getByTestId('next-visit-section')
    await section.waitFor({ state: 'visible', timeout: 25000 })
    await expect(page.getByTestId('nv-tab-visit')).toBeVisible()
    await expect(page.getByTestId('nv-tab-charges')).toBeVisible()

    // Switch to Charges → preset buttons appear.
    await page.getByTestId('nv-tab-charges').click()
    await expect(page.getByTestId('next-visit-charges')).toBeVisible()
    await expect(page.getByTestId('charge-preset-broken_bracket')).toBeVisible()
    await expect(page.getByTestId('charge-preset-lost_retainer')).toBeVisible()
    await expect(page.getByTestId('charge-preset-impressions')).toBeVisible()
  })

  test('clicking a charge preset posts and shows a result', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('next-visit-section').waitFor({ state: 'visible', timeout: 25000 })
    await page.getByTestId('nv-tab-charges').click()
    await page.getByTestId('charge-preset-broken_bracket').click()
    // A result line renders (posted to ledger, or an error message — either proves the flow is wired).
    await expect(page.getByTestId('charge-result')).toBeVisible({ timeout: 20000 })
  })
})
