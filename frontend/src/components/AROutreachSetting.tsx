import { useEffect, useState } from 'react'
import { BellRing } from 'lucide-react'
import { api } from '../lib/api'

/**
 * Owner/doctor switch for automatic collections reminders (30/60/90/120/180 days past due).
 * Off by default. Shown during initial setup and again in Settings.
 */
export default function AROutreachSetting() {
  const [enabled, setEnabled] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const res = await api.getArOutreach()
        if (res.ok && alive) setEnabled(!!(await res.json()).enabled)
      } catch { /* leave off */ }
      if (alive) setLoaded(true)
    })()
    return () => { alive = false }
  }, [])

  async function toggle() {
    const next = !enabled
    setSaving(true)
    setMsg('')
    try {
      const res = await api.setArOutreach(next)
      if (res.ok) { setEnabled(next); setMsg(next ? 'Automatic reminders are on.' : 'Automatic reminders are off.') }
      else setMsg(res.status === 403 ? 'Only the owner or doctor can change this.' : 'Could not save. Try again.')
    } catch { setMsg('Could not save. Try again.') }
    setSaving(false)
  }

  return (
    <div data-testid="ar-outreach-setting" className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 bg-teal-50 rounded-xl flex items-center justify-center flex-shrink-0">
            <BellRing size={18} className="text-teal-600" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-800">Automatic payment reminders</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-xl">
              Text patients a secure MyOrthoChart pay link when a payment is 30, 60, 90, 120 and 180 days past due, then stop.
              Only patients who agreed to text messages are contacted, only during office hours, and each reminder is sent once.
              You can still follow up manually from the Ledger either way.
            </p>
          </div>
        </div>
        <button
          data-testid="ar-outreach-toggle"
          role="switch"
          aria-checked={enabled}
          disabled={!loaded || saving}
          onClick={toggle}
          className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${enabled ? 'bg-teal-600' : 'bg-gray-300'}`}
        >
          <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
        </button>
      </div>
      {msg && <p data-testid="ar-outreach-msg" className="text-xs text-gray-600 mt-3">{msg}</p>}
    </div>
  )
}
