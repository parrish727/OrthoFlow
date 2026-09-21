// Date helpers.
//
// IMPORTANT: `new Date().toISOString().split('T')[0]` returns the *UTC* calendar date, which is
// WRONG for "today" in a practice's local timezone. After ~8 PM US-Eastern the UTC date has
// already rolled to tomorrow, so a UTC "today" shows an empty schedule/dashboard even though the
// demo data (seeded in Eastern time) is on the real local date.

const PRACTICE_TZ = 'America/New_York'

/**
 * Today's date anchored to the PRACTICE timezone (America/New_York), as YYYY-MM-DD.
 * Consistent regardless of where the browser/CI runner is (UTC containers included) and
 * matches the backend demo seed which anchors to Eastern time.
 */
export function localToday(): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: PRACTICE_TZ,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date())
}

/**
 * YYYY-MM-DD for a Date using its calendar-day components (browser-local). Use this for date
 * arithmetic where a Date object was built from a YYYY-MM-DD string (e.g. day shifting), so the
 * value round-trips without a UTC off-by-one. Do NOT use for computing "today" — use localToday().
 */
export function dateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// Back-compat alias: callers computing "today" should use localToday(); day-arithmetic uses dateStr().
export const localDateStr = dateStr
