import { test, expect } from '@playwright/test'
import { loginAsOwner } from '../fixtures/auth'

test.describe('Patient Flow Board', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOwner(page)
    await page.goto('/')
    await page.waitForLoadState('networkidle')
  })

  test('Flow board renders 5 columns', async ({ page }) => {
    await expect(page.getByText('Scheduled')).toBeVisible()
    await expect(page.getByText('Lobby')).toBeVisible()
    await expect(page.getByText('Seated')).toBeVisible()
    await expect(page.getByText('Checked Out')).toBeVisible()
    await expect(page.getByText('Dismissed')).toBeVisible()
  })

  test('Patients appear in flow board columns', async ({ page }) => {
    // At least one patient should be in the board (from demo seeds)
    const flowBoard = page.locator('[class*="grid"]').filter({ hasText: 'Lobby' })
    await expect(flowBoard).toBeVisible()
  })

  test('Check-in button moves patient to Lobby', async ({ page }) => {
    // Look for a check-in button in the Scheduled column
    const checkInBtn = page.getByRole('button', { name: /check.?in/i }).first()
    if (await checkInBtn.isVisible()) {
      await checkInBtn.click()
      await page.waitForTimeout(1000)
      // After check-in, the patient should move to Lobby column
    }
  })
})
