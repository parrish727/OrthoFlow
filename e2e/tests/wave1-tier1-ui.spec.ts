import { test, expect } from '@playwright/test'

// Wave 1 — Tier-1 UI edits:
//  • Dashboard: "needs attention" panel surfaced at top + patient search/jump bar
//  • Dashboard dedupe: MonthlyCalendar no longer duplicates the "handled automatically"
//    surface (AutomationActivity is the single source)
//  • Next Visit dropdown: Final Records + Retention Check removed; Aligner Refinement
//    Deliver + Appliance Check added
//  • Appliance dropdown: non-ortho types removed; new ortho appliances added
test.describe('Wave 1 — Tier-1 UI', () => {
  test('dashboard shows attention panel at top + patient search bar', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    // Needs-attention panel present at top of the dashboard.
    await page.getByTestId('ai-assist').waitFor({ state: 'visible', timeout: 20000 })
    // Patient search / jump bar present.
    const search = page.getByTestId('dashboard-patient-search')
    await expect(search).toBeVisible()
    await search.locator('input').fill('Kno')
    // Results dropdown appears with the flagship patient (Priscilla Knowles).
    await page.getByTestId('dashboard-patient-results').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByText(/Knowles/i).first()).toBeVisible()
  })

  test('dashboard no longer duplicates the "handled automatically" surface', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('automation-activity').waitFor({ state: 'visible', timeout: 20000 })
    // AutomationActivity is the single "handled automatically" surface.
    await expect(page.getByText('OrthoFlow handled this automatically')).toBeVisible()
    // Calendar day cells no longer carry a per-day "done" (handled automatically) indicator.
    await page.getByTestId('monthly-calendar').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('monthly-calendar').getByText(/\bdone\b/).first()).toHaveCount(0)
  })
})
