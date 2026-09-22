import { useState } from 'react'
import { ClipboardList, Users, UserPlus, PlayCircle, Stethoscope, Loader2, Printer, ChevronRight } from 'lucide-react'
import { api } from '../lib/api'

// Front-office / TC report suite (Wave 4). Pulls pending, observation, new-patient, start-scheduled,
// and doctor-referral reports with scheduled vs non-scheduled splits. Printable.
interface Row { patient_id: string; first_name: string; last_name: string; status?: string; has_upcoming?: boolean; phone?: string | null }
interface Referrer { referring_doctor: string; patient_count: number }
interface CategoryResult {
  category: string; count: number; rows?: Row[]; referrers?: Referrer[]
  scheduled_count?: number; non_scheduled_count?: number
  by_level?: Record<string, { count: number; scheduled_count: number; non_scheduled_count: number }>
}

const CATS: { key: string; label: string; icon: typeof Users; path: string }[] = [
  { key: 'pending', label: 'Pending (need follow-up)', icon: ClipboardList, path: 'pending' },
  { key: 'observation', label: 'Observation 1–4', icon: Users, path: 'observation' },
  { key: 'new_patient_added', label: 'New Patient Added', icon: UserPlus, path: 'new-patient-added' },
  { key: 'start_scheduled', label: 'Start Scheduled', icon: PlayCircle, path: 'start-scheduled' },
  { key: 'doctor_referral', label: 'Doctor Referral', icon: Stethoscope, path: 'doctor-referral' },
]

export default function TCReportSuite() {
  const [active, setActive] = useState<string | null>(null)
  const [result, setResult] = useState<CategoryResult | null>(null)
  const [loading, setLoading] = useState(false)

  async function run(path: string, key: string) {
    setActive(key); setLoading(true); setResult(null)
    try {
      const r = await api.reportCategory(path)
      if (r.ok) setResult(await r.json())
    } catch { /* handled */ }
    setLoading(false)
  }

  return (
    <div data-testid="tc-report-suite">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mb-4">
        {CATS.map(c => (
          <button
            key={c.key}
            data-testid={`tc-report-${c.key}`}
            onClick={() => run(c.path, c.key)}
            className={`flex items-center gap-2 px-3 py-2.5 rounded-xl border text-xs font-medium transition-colors ${active === c.key ? 'bg-teal-50 border-teal-300 text-teal-700' : 'bg-white border-gray-200 text-gray-600 hover:border-teal-200'}`}
          >
            <c.icon size={14} /> {c.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="bg-white rounded-2xl border border-gray-200/80 p-8 text-center"><Loader2 size={18} className="animate-spin text-gray-400 mx-auto" /></div>
      ) : result ? (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="tc-report-result">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-3">
            <h3 className="text-sm font-semibold text-gray-800 capitalize">{result.category.replace(/_/g, ' ')}</h3>
            <span className="text-xs text-gray-400">{result.count} total</span>
            {result.scheduled_count != null && (
              <span className="text-[11px] text-gray-500 ml-2">Scheduled {result.scheduled_count} · Non-scheduled {result.non_scheduled_count}</span>
            )}
            <button onClick={() => window.print()} className="ml-auto flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700"><Printer size={13} /> Print</button>
          </div>

          {result.by_level && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-4 border-b border-gray-100">
              {Object.entries(result.by_level).map(([lvl, v]) => (
                <div key={lvl} className="rounded-xl border border-gray-100 p-3">
                  <p className="text-xs font-medium text-gray-700 capitalize">{lvl.replace('_', ' ')}</p>
                  <p className="text-lg font-bold text-gray-900">{v.count}</p>
                  <p className="text-[10px] text-gray-400">Sched {v.scheduled_count} · Non {v.non_scheduled_count}</p>
                </div>
              ))}
            </div>
          )}

          {result.referrers ? (
            <div className="divide-y divide-gray-50 max-h-[420px] overflow-y-auto">
              {result.referrers.map((r, i) => (
                <div key={i} className="px-5 py-2.5 flex items-center justify-between text-sm">
                  <span className="text-gray-800">{r.referring_doctor}</span>
                  <span className="font-medium text-gray-900">{r.patient_count} patient{r.patient_count === 1 ? '' : 's'}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="divide-y divide-gray-50 max-h-[420px] overflow-y-auto">
              {(result.rows || []).length === 0 ? (
                <p className="px-5 py-8 text-sm text-gray-400 text-center">No patients in this report.</p>
              ) : (result.rows || []).map(r => (
                <div key={r.patient_id} className="px-5 py-2.5 flex items-center justify-between gap-3 text-sm" data-testid="tc-report-row">
                  <div className="min-w-0">
                    <span className="font-medium text-gray-800">{r.last_name}, {r.first_name}</span>
                    <span className="text-xs text-gray-400 ml-2">{r.status ? r.status.replace('_', ' ') : ''}</span>
                  </div>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${r.has_upcoming ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                    {r.has_upcoming ? 'Scheduled' : 'Not scheduled'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-gray-200/80 p-8 text-center text-sm text-gray-400">
          <ChevronRight size={20} className="mx-auto text-gray-300 mb-2" /> Pick a report above.
        </div>
      )}
    </div>
  )
}
