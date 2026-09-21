import { test, expect } from '@playwright/test'

// Phase 2 — Insurance lifetime-benefit rework. Ortho has NO co-pay; benefit is a lifetime
// maximum. The plan detail must show Lifetime Max / Used / Remaining Benefit and must NOT
// show "Copay" or "Annual Remaining".
// Patient e0689401 has a primary plan with an ortho lifetime max.
const PATIENT = 'e0689401-9966-4799-8f30-b5b81e25e8d2'

test.describe('Insurance — ortho lifetime benefit (no co-pay)', () => {
  test('plan detail shows lifetime-benefit metrics and no co-pay/annual', async ({ page }) => {
    await page.goto('/insurance')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('insurance-page').waitFor({ state: 'visible', timeout: 20000 })

    // Expand this patient's panel.
    await page.getByTestId(`roster-row-${PATIENT}`).click()
    await page.getByTestId(`patient-panel-${PATIENT}`).waitFor({ state: 'visible', timeout: 20000 })
    const panel = page.getByTestId(`patient-panel-${PATIENT}`)

    // New lifetime-benefit labels present.
    await expect(panel.getByText('Remaining Benefit')).toBeVisible()
    await expect(panel.getByText('Lifetime Max')).toBeVisible()

    // Legacy ortho-irrelevant labels gone.
    await expect(panel.getByText('Copay', { exact: true })).toHaveCount(0)
    await expect(panel.getByText('Annual Remaining')).toHaveCount(0)
  })
})
