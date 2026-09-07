import { Page } from '@playwright/test'

const STAFF_PASSWORD = 'Demo2026!'
const PATIENT_PASSWORD = 'Demo2026!'

const ACCOUNTS = {
  owner: 'demo@orthoflowsolutions.com',
  doctor: 'demo-doctor@orthoflowsolutions.com',
  manager: 'demo-manager@orthoflowsolutions.com',
  da: 'demo-da@orthoflowsolutions.com',
  frontDesk: 'demo-frontdesk@orthoflowsolutions.com',
  patient: 'priscilla.knowles@melanin-tech.com',
}

async function staffLogin(page: Page, email: string): Promise<void> {
  await page.goto('/login')
  await page.locator('input[type="email"]').fill(email)
  await page.locator('input[type="password"]').fill(STAFF_PASSWORD)
  // Submit and wait for the login API response directly (resilient to CDN latency).
  const [resp] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/auth/login') && r.request().method() === 'POST', { timeout: 30000 }),
    page.getByRole('button', { name: /sign in|log in/i }).click(),
  ])
  if (!resp.ok()) throw new Error(`Login failed: ${resp.status()}`)
  await page.waitForFunction(() => !!localStorage.getItem('token'), { timeout: 15000 })
  await page.waitForTimeout(500)
}

export async function loginAsOwner(page: Page): Promise<void> {
  await staffLogin(page, ACCOUNTS.owner)
}

export async function loginAsDoctor(page: Page): Promise<void> {
  await staffLogin(page, ACCOUNTS.doctor)
}

export async function loginAsManager(page: Page): Promise<void> {
  await staffLogin(page, ACCOUNTS.manager)
}

export async function loginAsDA(page: Page): Promise<void> {
  await staffLogin(page, ACCOUNTS.da)
}

export async function loginAsFrontDesk(page: Page): Promise<void> {
  await staffLogin(page, ACCOUNTS.frontDesk)
}

export async function loginAsPatient(page: Page): Promise<void> {
  await page.goto('/portal')
  await page.getByPlaceholder('Email').fill(ACCOUNTS.patient)
  await page.getByPlaceholder('Password').fill(PATIENT_PASSWORD)
  await page.getByRole('button', { name: /sign in|log in/i }).click()
  await page.waitForTimeout(2000)
}

export { ACCOUNTS, STAFF_PASSWORD, PATIENT_PASSWORD }
