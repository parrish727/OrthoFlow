import { test, expect } from '@playwright/test'

// Session from global-setup storageState.

test.describe('Reports — categories', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/reports')
    await page.waitForLoadState('networkidle')
    // Categories load async — wait for the grid to populate.
    await page.getByTestId('report-cat-patients_owe').waitFor({ state: 'visible', timeout: 15000 })
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

  test('consults-need-verification category is available', async ({ page }) => {
    await expect(page.getByTestId('report-cat-consults_need_verification')).toBeVisible()
    await page.getByTestId('report-cat-consults_need_verification').click()
    await expect(page.getByTestId('category-report-result')).toBeVisible({ timeout: 15000 })
  })
})

test.describe('OrthoFlow AI Assist', () => {
  test('AI assist widget renders on the dashboard', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('ai-assist').waitFor({ state: 'attached', timeout: 20000 })
    await expect(page.getByText('OrthoFlow AI — What needs attention')).toBeVisible()
  })

  test('automation activity widget renders + run-now works', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('automation-activity').waitFor({ state: 'attached', timeout: 20000 })
    await expect(page.getByText('OrthoFlow handled this automatically')).toBeVisible()
    // Trigger the automation engine on demand and confirm the request succeeds.
    const [resp] = await Promise.all([
      page.waitForResponse(r => r.url().includes('/automation/run') && r.request().method() === 'POST', { timeout: 20000 }),
      page.getByTestId('automation-run-now').click(),
    ])
    expect(resp.status()).toBe(200)
  })

  test('practice impact card leads with claims, savings, efficiency', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('practice-impact').waitFor({ state: 'attached', timeout: 20000 })
    await expect(page.getByText('OrthoFlow AI — Practice Impact')).toBeVisible()
    await expect(page.getByTestId('impact-claims')).toBeAttached()
    await expect(page.getByTestId('impact-savings')).toBeAttached()
    await expect(page.getByTestId('impact-efficiency')).toBeAttached()
  })
})

test.describe('Schedule — Medicaid MC + owe indicator', () => {
  test('schedule renders appointment cards', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')
    // Wait for at least one appointment card to render (schedule is data-heavy).
    await page.locator('[data-testid^="appt-patient-"]').first().waitFor({ state: 'visible', timeout: 20000 })
    expect(await page.locator('[data-testid^="appt-patient-"]').count()).toBeGreaterThan(0)
  })
})

test.describe('Patient ortho panel — comments + chart charges', () => {
  test('ortho panel renders with comments + chart charge sections', async ({ page }) => {
    // Direct navigation to Priscilla Knowles (prime demo patient) avoids multi-hop flakiness.
    await page.goto('/patients/78c5125a-32a9-44b9-9ff0-a63931713bb0')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)
    // Panel is far down the long PatientDetail page. Assert DOM presence (attached) — it
    // renders whenever the patient id is present; the mutation behavior is covered by API tests.
    await expect(page.getByTestId('patient-ortho-panel')).toBeAttached({ timeout: 25000 })
    await expect(page.getByTestId('comments-tab-info')).toBeAttached()
    await expect(page.getByTestId('comment-input')).toBeAttached()
    await expect(page.getByTestId('charge-cdt')).toBeAttached()
  })
})
