import { test, expect } from '@playwright/test'

// Wave 2 — Today's Charges + Claims popup + Ledger AI drill-down + Imaging record types.
// Flagship patient: Priscilla Knowles.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Wave 2 — charges / claims / ledger / imaging', () => {
  test("Today's Charges panel has a CDT preset dropdown + full-width description", async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    const panel = page.getByTestId('todays-charges')
    await panel.waitFor({ state: 'visible', timeout: 20000 })
    await expect(panel.getByText("Today's Charges")).toBeVisible()
    // Preset dropdown present with the ortho presets.
    const preset = page.getByTestId('charge-preset')
    await expect(preset).toBeVisible()
    await expect(preset.locator('option', { hasText: 'Office Visit' })).toHaveCount(1)
    await expect(preset.locator('option', { hasText: 'Upper Essix' })).toHaveCount(1)
    // Selecting a preset fills CDT + fee.
    await preset.selectOption({ label: /Upper Lingual Retainer/ })
    await expect(page.getByTestId('charge-cdt')).toHaveValue(/D86|D89/)
    await expect(page.getByTestId('charge-description')).not.toHaveValue('')
  })

  test('Claims: clicking a patient opens a popup (stays on Claims page)', async ({ page }) => {
    await page.goto('/claims')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('claims-roster').waitFor({ state: 'visible', timeout: 20000 })
    await page.getByTestId(`claims-row-${PRISCILLA}`).click()
    // A modal popup opens; URL stays on /claims (does not navigate away / kick out).
    await page.getByTestId('claims-modal').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page).toHaveURL(/\/claims/)
    await expect(page.getByTestId(`claims-panel-${PRISCILLA}`)).toBeVisible()
    await page.getByTestId('claims-modal-close').click()
    await expect(page.getByTestId('claims-modal')).toHaveCount(0)
  })

  test('Ledger AI insight drills down to source claims/findings', async ({ page }) => {
    await page.goto('/ledger')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('practice-impact').waitFor({ state: 'visible', timeout: 20000 })
    // Click the first claims impact item → drill-down modal with method + sources.
    await page.getByTestId('impact-item-claims').first().click()
    await page.getByTestId('impact-drilldown').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByText('How this was calculated:')).toBeVisible()
    await page.getByTestId('impact-drilldown-close').click()
    await expect(page.getByTestId('impact-drilldown')).toHaveCount(0)
  })

  test('Imaging upload has a Record Type dropdown', async ({ page }) => {
    await page.goto('/imaging')
    await page.waitForLoadState('networkidle')
    // Select the flagship patient so the upload form renders.
    await page.getByPlaceholder('Search patients by name...').fill('Priscilla')
    const hit = page.getByText('Priscilla Knowles').first()
    await hit.click({ timeout: 20000 }).catch(() => {})
    const recordType = page.getByTestId('upload-record-type')
    await recordType.waitFor({ state: 'visible', timeout: 20000 })
    await expect(recordType.locator('option', { hasText: 'Progress Records' })).toHaveCount(1)
    await expect(recordType.locator('option', { hasText: 'Initial Records' })).toHaveCount(1)
  })
})
