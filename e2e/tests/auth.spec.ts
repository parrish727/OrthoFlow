import { test, expect } from '@playwright/test'
import { loginAsOwner, loginAsDoctor, loginAsManager, loginAsDA, loginAsFrontDesk, loginAsPatient, ACCOUNTS } from '../fixtures/auth'

test.describe('Staff Authentication', () => {
  test('Owner can log in', async ({ page }) => {
    await loginAsOwner(page)
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Doctor can log in', async ({ page }) => {
    await loginAsDoctor(page)
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Office Manager can log in', async ({ page }) => {
    await loginAsManager(page)
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Dental Assistant can log in', async ({ page }) => {
    await loginAsDA(page)
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Front Desk can log in', async ({ page }) => {
    await loginAsFrontDesk(page)
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Invalid login is rejected', async ({ page }) => {
    await page.goto('/login')
    await page.getByPlaceholder('Email').fill('invalid@example.com')
    await page.getByPlaceholder('Password').fill('wrongpassword')
    await page.getByRole('button', { name: /sign in|log in/i }).click()
    await expect(page.getByText(/invalid|error|failed/i)).toBeVisible({ timeout: 5000 })
  })
})

test.describe('Patient Portal Authentication', () => {
  test('Patient can log in to portal', async ({ page }) => {
    await loginAsPatient(page)
    await expect(page.getByText(/welcome|dashboard|appointment/i)).toBeVisible({ timeout: 5000 })
  })

  test('Invalid patient login is rejected', async ({ page }) => {
    await page.goto('/portal')
    await page.getByPlaceholder('Email').fill('bad@example.com')
    await page.getByPlaceholder('Password').fill('wrong')
    await page.getByRole('button', { name: /sign in|log in/i }).click()
    await expect(page.getByText(/invalid|error|failed/i)).toBeVisible({ timeout: 5000 })
  })
})
