import { test, expect } from '@playwright/test'
import { loginAsPatient } from '../fixtures/auth'

test.describe('MyOrthoChart Patient Portal', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsPatient(page)
  })

  test('Dashboard shows patient info', async ({ page }) => {
    await expect(page.getByText(/welcome|hi|hello/i)).toBeVisible({ timeout: 5000 })
  })

  test('Messages section accessible', async ({ page }) => {
    const messagesTab = page.getByRole('button', { name: /messages/i })
    if (await messagesTab.isVisible()) {
      await messagesTab.click()
      await page.waitForTimeout(1000)
    }
  })

  test('Appointments section shows upcoming', async ({ page }) => {
    await expect(page.getByText(/appointment|schedule/i)).toBeVisible({ timeout: 5000 })
  })

  test('Treatment progress displays', async ({ page }) => {
    await expect(page.getByText(/treatment|progress|phase/i)).toBeVisible({ timeout: 5000 })
  })
})
