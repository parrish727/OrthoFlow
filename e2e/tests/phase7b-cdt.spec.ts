import { test, expect } from '@playwright/test'

// Phase 7b-7 — Custom (practice-defined) CDT codes surfaced on the CDT Codes page:
// create form + list. Backend CustomCDTCode + /ortho/cdt/custom (GET/POST) already exist.
test.describe('Phase 7b — Custom CDT codes', () => {
  test('CDT Codes page shows a Custom Codes section with an add control', async ({ page }) => {
    await page.goto('/cdt-codes')
    await page.waitForLoadState('networkidle')

    await page.getByTestId('custom-cdt-section').waitFor({ state: 'visible', timeout: 25000 })
    await expect(page.getByText('Custom Codes', { exact: true })).toBeVisible()
    await expect(page.getByTestId('custom-cdt-add')).toBeVisible()
  })

  test('the new-custom-code form opens and accepts input', async ({ page }) => {
    await page.goto('/cdt-codes')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('custom-cdt-section').waitFor({ state: 'visible', timeout: 25000 })

    await page.getByTestId('custom-cdt-add').click()
    await page.getByTestId('custom-cdt-form').waitFor({ state: 'visible', timeout: 10000 })

    const code = `D8999-${Date.now().toString().slice(-5)}`
    await page.getByTestId('custom-cdt-code').fill(code)
    await page.getByTestId('custom-cdt-desc').fill('E2E custom procedure')
    await page.getByTestId('custom-cdt-fee').fill('60')
    await expect(page.getByTestId('custom-cdt-code')).toHaveValue(code)
    await expect(page.getByTestId('custom-cdt-save')).toBeEnabled()
  })
})
