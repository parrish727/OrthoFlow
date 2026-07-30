import { test, expect } from '@playwright/test'
import { loginAsOwner, loginAsDA } from '../fixtures/auth'

test.describe('Role-Based Access Control', () => {
  test('Owner sees full navigation', async ({ page }) => {
    await loginAsOwner(page)
    await expect(page.getByText('Ledger')).toBeVisible()
    await expect(page.getByText('Reports')).toBeVisible()
    await expect(page.getByText('Settings')).toBeVisible()
  })

  test('DA sees limited navigation (no Finance)', async ({ page }) => {
    await loginAsDA(page)
    await expect(page.getByText('Schedule')).toBeVisible()
    await expect(page.getByText('Patients')).toBeVisible()
    // DA should NOT see Finance items
    await expect(page.getByText('Ledger')).not.toBeVisible()
    await expect(page.getByText('Invoices')).not.toBeVisible()
  })

  test('Owner can access Staff Permissions', async ({ page }) => {
    await loginAsOwner(page)
    await page.goto('/settings/permissions')
    await expect(page.getByText('Staff Permissions')).toBeVisible()
    await expect(page.getByText('Staff Members')).toBeVisible()
  })

  test('DA cannot access Staff Permissions', async ({ page }) => {
    await loginAsDA(page)
    await page.goto('/settings/permissions')
    // Should be redirected or show access denied
    await page.waitForTimeout(2000)
    const url = page.url()
    // DA should not see the permissions page content
    const hasDenied = await page.getByText(/access denied|only owner/i).isVisible().catch(() => false)
    const wasRedirected = !url.includes('/settings/permissions')
    expect(hasDenied || wasRedirected).toBe(true)
  })
})
