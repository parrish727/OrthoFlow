import { test, expect } from '@playwright/test'
import { loginAsOwner } from '../fixtures/auth'

test.describe('Communications', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOwner(page)
  })

  test('Communications page loads', async ({ page }) => {
    await page.goto('/communications')
    await expect(page.getByRole('heading', { name: 'Communications' })).toBeVisible()
  })

  test('Active Virtual Visits card renders', async ({ page }) => {
    await page.goto('/communications')
    await expect(page.getByText('Active Virtual Visits')).toBeVisible()
  })

  test('Patient Messages page loads', async ({ page }) => {
    await page.goto('/patient-messages')
    await expect(page.getByText('Patient Messages')).toBeVisible()
  })

  test('Schedule page loads with today view', async ({ page }) => {
    await page.goto('/schedule')
    await page.waitForLoadState('networkidle')
    await expect(page.getByText(/today|schedule/i)).toBeVisible()
  })
})
