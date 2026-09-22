import { test, expect } from '@playwright/test'

// Phase 7b-8 — AI usage-based customization suggestions on the AI Letters page.
// Backend /ai/letters/suggestions ranks letter types by DoctorLetterStyle.use_count; the page
// surfaces the doctor's most-used types as one-click chips. School usage is seeded for the demo user.
test.describe('Phase 7b — AI usage suggestions (Letters)', () => {
  test('AI Letters page surfaces usage-based suggestions and selecting one sets the letter type', async ({ page }) => {
    await page.goto('/ai-letters')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('ai-letters-page').waitFor({ state: 'visible', timeout: 25000 })

    // The suggestions strip renders (seeded school usage) with at least one suggestion chip.
    const strip = page.getByTestId('letter-suggestions')
    await strip.waitFor({ state: 'visible', timeout: 20000 })
    const chip = page.getByTestId('suggestion-school')
    await expect(chip).toBeVisible()
    await expect(chip).toContainText('×') // shows a usage count like "6×"

    // One-click selects that letter type in the controls.
    await chip.click()
    await expect(page.getByTestId('letter-type')).toHaveValue('school')
  })
})
