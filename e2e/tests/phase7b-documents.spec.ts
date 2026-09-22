import { test, expect } from '@playwright/test'

// Phase 7b-4 — Documents visible inside the clinical chart + a dedicated Documents tab.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Phase 7b — Documents in clinical chart + Documents tab', () => {
  test('clinical chart shows a Documents section', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    // Clinical tab is default; the Documents section is embedded.
    await page.getByTestId('clinical-documents').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('clinical-documents-list')).toBeVisible()
    await expect(page.getByTestId('clinical-documents-viewall')).toBeVisible()
  })

  test('Documents tab exists and shows the documents panel', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('patient-tabs').waitFor({ state: 'attached', timeout: 20000 })

    // The Documents tab is present next to Clinical/Administrative.
    await expect(page.getByTestId('patient-tab-documents')).toBeVisible()
    await page.getByTestId('patient-tab-documents').click()

    // Documents panel + its list render; clinical + admin panels hide.
    await expect(page.getByTestId('patient-documents-panel')).toBeVisible()
    await expect(page.getByTestId('documents-tab-list')).toBeVisible()
    await expect(page.getByTestId('patient-clinical-panel')).toBeHidden()
    await expect(page.getByTestId('patient-administrative-panel')).toBeHidden()
  })

  test('View all link from clinical chart jumps to the Documents tab', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('clinical-documents-viewall').waitFor({ state: 'visible', timeout: 20000 })
    await page.getByTestId('clinical-documents-viewall').click()
    await expect(page.getByTestId('patient-documents-panel')).toBeVisible()
    await expect(page.getByTestId('documents-tab-list')).toBeVisible()
  })
})
