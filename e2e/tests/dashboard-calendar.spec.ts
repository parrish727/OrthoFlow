import { test, expect } from '@playwright/test'

// Phase 5 — Dashboard monthly calendar (replaces Today's Huddle) + Patient Flow as its own tab.
test.describe('Dashboard monthly calendar + Patient Flow tab', () => {
  test('dashboard shows the monthly calendar and not the old huddle', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('monthly-calendar').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByText('Monthly Calendar')).toBeVisible()
    // Old huddle heading is gone from the dashboard.
    await expect(page.getByText("Today's Huddle")).toHaveCount(0)
    // Resize control present (resizable calendar).
    await expect(page.getByTestId('calendar-resize')).toBeVisible()
  })

  test('Patient Flow has its own page/route', async ({ page }) => {
    await page.goto('/patient-flow')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('patient-flow-page').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByRole('heading', { name: 'Patient Flow', exact: true })).toBeVisible()
    // It is no longer embedded on the dashboard.
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('monthly-calendar').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page.getByTestId('patient-flow-page')).toHaveCount(0)
  })

  test('clicking a calendar day expands an in-place day detail (no navigation away)', async ({ page }) => {
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('monthly-calendar').waitFor({ state: 'visible', timeout: 20000 })

    // Click today's cell — a detail panel expands inside the calendar; URL stays on the dashboard.
    const today = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
    await page.getByTestId(`calendar-day-${today}`).click()
    await page.getByTestId('calendar-day-detail').waitFor({ state: 'visible', timeout: 20000 })
    await expect(page).toHaveURL(/\/$|\/#?$/)
    // Today has seeded appointments → at least one appt row in the detail.
    await expect(page.locator('[data-testid="day-detail-appt"]').first()).toBeVisible({ timeout: 20000 })
  })
})
