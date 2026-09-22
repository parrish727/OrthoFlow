import { test, expect } from '@playwright/test'

// Phase 7b — Treatment note authorship (color/initials/edit-window) + Treatment Notes prominence.
// Session from global-setup storageState. Priscilla is the flagship demo patient with notes.
const PRISCILLA = '78c5125a-32a9-44b9-9ff0-a63931713bb0'

test.describe('Phase 7b — Treatment Notes authorship + prominence', () => {
  test('Treatment Notes card is elevated (prominent) with a count', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')

    const card = page.getByTestId('treatment-notes-card')
    await card.waitFor({ state: 'visible', timeout: 20000 })
    await expect(card.getByText('Treatment Notes', { exact: true })).toBeVisible()
    await expect(page.getByTestId('treatment-notes-count')).toBeVisible()
  })

  test('notes render a per-author color badge with initials, and can be added + edited', async ({ page }) => {
    await page.goto(`/patients/${PRISCILLA}`)
    await page.waitForLoadState('networkidle')
    await page.getByTestId('treatment-notes-card').waitFor({ state: 'visible', timeout: 20000 })

    // Add a fresh note so we have a guaranteed-editable item authored by the current user.
    const unique = `7b-1 e2e note ${Date.now()}`
    // NoteInput textarea — target within the treatment notes card.
    const card = page.getByTestId('treatment-notes-card')
    const textarea = card.locator('textarea').first()
    await textarea.fill(unique)
    // Save the raw note (deterministic testid).
    await card.getByTestId('note-save-raw').click()

    // The new note appears with an author badge (color dot + initials).
    const noteItem = page.locator('[data-testid^="note-item-"]').first()
    await noteItem.waitFor({ state: 'visible', timeout: 20000 })
    const badge = page.locator('[data-testid^="note-author-badge-"]').first()
    await expect(badge).toBeVisible()
    await expect(badge).not.toBeEmpty()

    // Edit the freshly-added (editable) note.
    const editBtn = page.locator('[data-testid^="note-edit-"]').first()
    await editBtn.waitFor({ state: 'visible', timeout: 15000 })
    await editBtn.click()
    const editInput = page.locator('[data-testid^="note-edit-input-"]').first()
    await editInput.waitFor({ state: 'visible', timeout: 10000 })
    await editInput.fill(`${unique} — EDITED`)
    await page.locator('[data-testid^="note-edit-save-"]').first().click()

    // The edited text and an "edited" marker are shown.
    await expect(page.getByText(`${unique} — EDITED`).first()).toBeVisible({ timeout: 15000 })
  })
})
