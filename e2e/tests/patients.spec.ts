import { test, expect } from '@playwright/test'
import { loginAsOwner } from '../fixtures/auth'

test.describe('Patient Management', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsOwner(page)
    await page.goto('/patients')
    await page.waitForLoadState('networkidle')
  })

  test('Patient list loads', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Patients' })).toBeVisible()
    await expect(page.getByText(/patient/i)).toBeVisible()
  })

  test('Search patients by name', async ({ page }) => {
    await page.getByPlaceholder('Search patients').fill('Priscilla')
    await page.waitForTimeout(500)
    await expect(page.getByText('Knowles')).toBeVisible()
  })

  test('Expand patient info panel', async ({ page }) => {
    const infoButton = page.locator('button[title="View patient info"]').first()
    await infoButton.click()
    await expect(page.getByText('First Name')).toBeVisible()
    await expect(page.getByText('Date of Birth')).toBeVisible()
    await expect(page.getByText('Chart #')).toBeVisible()
  })

  test('Create new patient modal opens', async ({ page }) => {
    await page.getByRole('button', { name: /new patient/i }).click()
    await expect(page.getByRole('heading', { name: 'New Patient' })).toBeVisible()
    await expect(page.getByText('First Name')).toBeVisible()
    await expect(page.getByText('Last Name')).toBeVisible()
  })

  test('Create patient with required fields', async ({ page }) => {
    await page.getByRole('button', { name: /new patient/i }).click()
    await page.locator('input').filter({ hasText: '' }).nth(0).fill('Test')
    await page.locator('form input[required]').first().fill('Test')
    await page.locator('form input[required]').last().fill('Patient')
    await page.getByRole('button', { name: /create patient/i }).click()
    await page.waitForTimeout(2000)
  })

  test('Navigate to patient detail', async ({ page }) => {
    const firstPatient = page.locator('[class*="gradient-to-br"]').first()
    await firstPatient.click()
    await page.waitForURL(/\/patients\//)
  })
})
