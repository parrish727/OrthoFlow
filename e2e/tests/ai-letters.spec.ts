import { test, expect } from '@playwright/test'

// Phase 7 — Multi-type AI Letters with Gmail-style polish + per-doctor style learning.
// Generation calls live Claude, so use generous timeouts.
test.describe('AI Letters', () => {
  test('generate a school note, polish it, and save style', async ({ page }) => {
    test.setTimeout(90000)
    await page.goto('/ai-letters')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('ai-letters-page').waitFor({ state: 'visible', timeout: 20000 })

    // Pick a letter type and generate.
    await page.getByTestId('letter-type').selectOption('school')
    await page.getByTestId('generate-letter').click()

    // The generated letter fills the editor (wait for non-empty content).
    await expect.poll(async () => (await page.getByTestId('letter-text').inputValue()).length, { timeout: 60000 }).toBeGreaterThan(40)

    // Gmail-style polish: make it shorter.
    const before = await page.getByTestId('letter-text').inputValue()
    await page.getByTestId('polish-shorter').click()
    await expect.poll(async () => (await page.getByTestId('letter-text').inputValue()), { timeout: 60000 }).not.toBe(before)

    // Teach my style (save sample).
    await page.getByTestId('save-style').click()
    await expect(page.getByTestId('save-style')).toContainText('Saved', { timeout: 20000 })
  })
})
