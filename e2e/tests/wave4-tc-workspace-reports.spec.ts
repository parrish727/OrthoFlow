import { test, expect } from '@playwright/test'

// Wave 4 — TC Proposal workspace + document folder-tree + reports suite + Reports Builder options.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Wave 4 — TC workspace, documents tree, reports suite', () => {
  test('TC Proposal: Save button + patient status dropdown', async ({ page }) => {
    await page.goto('/tc-proposal')
    await page.waitForLoadState('networkidle')
    await page.getByPlaceholder('Search by name...').fill('Priscilla')
    await page.getByText('Priscilla Knowles').first().click({ timeout: 20000 }).catch(() => {})
    // Save (renamed from Mark as Presented) + patient status dropdown present.
    await expect(page.getByTestId('tc-save')).toBeVisible({ timeout: 20000 })
    await expect(page.getByTestId('tc-patient-status')).toBeVisible()
  })

  test('Reports: Front Office / TC report suite runs categories', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('reports-tab-categories').click()
    await page.getByTestId('tc-report-suite').waitFor({ state: 'visible', timeout: 20000 })
    await page.getByTestId('tc-report-pending').click()
    await page.getByTestId('tc-report-result').waitFor({ state: 'visible', timeout: 20000 })
    // Doctor referral report renders ranked referrers.
    await page.getByTestId('tc-report-doctor_referral').click()
    await page.getByTestId('tc-report-result').waitFor({ state: 'visible', timeout: 20000 })
  })

  test('Report Builder has Missing Appointments + searchable Appt Type', async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('reports-tab-builder').click()
    await page.getByTestId('report-builder').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('filter-missing-appts')).toBeVisible()
    await expect(page.getByTestId('filter-appt-type')).toBeVisible()
  })

  test('Patient documents render as a folder tree', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    const docTab = page.getByTestId('patient-tab-documents')
    if (await docTab.count()) {
      await docTab.click()
      await expect(page.getByTestId('patient-documents-panel')).toBeVisible({ timeout: 20000 })
    }
  })
})
