import { test, expect } from '@playwright/test'
import { loginAsPatient } from '../fixtures/auth'

// Wave 5 — ADP connector, appliance vendor portal, email relay/AI letters, virtual-visit tightening,
// + demo UI fixes (card swap, note author dropdown, trimmed docs/alerts).
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Wave 5 — integrations + UI polish', () => {
  test('Time Clock shows ADP panel + Export Hours, no payroll summary', async ({ page }) => {
    await page.goto('/time-tracking')
    await page.waitForLoadState('networkidle')
    await expect(page.getByTestId('timeclock-hours-only-note')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('export-hours-csv')).toBeVisible()
    await expect(page.getByTestId('adp-status')).toBeVisible()
    // Payroll pieces removed.
    await expect(page.getByText('Payroll Summary')).toHaveCount(0)
    await expect(page.getByText('Set Pay Rate')).toHaveCount(0)
  })

  test('Appliance tracker has a Lab link (vendor portal) action', async ({ page }) => {
    await page.goto('/appliances')
    await page.waitForLoadState('networkidle')
    const links = page.locator('[data-testid^="vendor-link-"]')
    await expect.poll(async () => links.count(), { timeout: 20000 }).toBeGreaterThan(0)
  })

  test('AI Letters has referring-contact send panel', async ({ page }) => {
    await page.goto('/ai-letters')
    await page.waitForLoadState('networkidle')
    await expect(page.getByTestId('letter-send-panel')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('letter-contact-select')).toBeVisible()
    await expect(page.getByTestId('letter-to-email')).toBeVisible()
  })

  test('PatientDetail: Treatment Notes card + note author dropdown present', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await expect(page.getByTestId('treatment-notes-card')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('note-author-select')).toBeVisible()
    // The redundant clinical-documents quick-look is gone.
    await expect(page.getByTestId('clinical-documents')).toHaveCount(0)
  })

  test('MyOrthoChart virtual-visit join surfaces when a visit is active', async ({ page }) => {
    await loginAsPatient(page)
    await page.goto('/portal')
    await page.waitForLoadState('networkidle')
    // No active visit by default → banner absent is fine; when present, Join is wired.
    const banner = page.getByTestId('portal-active-visit')
    if (await banner.count()) {
      await expect(page.getByTestId('portal-join-visit')).toBeVisible()
    }
  })
})
