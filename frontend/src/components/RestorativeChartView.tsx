/**
 * RestorativeChartView — displays per-tooth conditions and restoration history.
 * Fetches from /api/v1/restorative/patients/{id}/chart
 */
import { useState, useEffect } from 'react'
import { Plus } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
function authFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('token')
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
}

interface Restoration {
  id: string
  tooth_number: number
  surfaces: string | null
  restoration_type: string
  material: string | null
  status: string
  cdt_code: string | null
  date_placed: string | null
}

const CONDITION_COLORS: Record<string, string> = {
  healthy: 'bg-green-100 text-green-700',
  caries: 'bg-red-100 text-red-700',
  fractured: 'bg-orange-100 text-orange-700',
  missing: 'bg-gray-200 text-gray-500',
  impacted: 'bg-purple-100 text-purple-700',
}

const STATUS_COLORS: Record<string, string> = {
  existing: 'bg-gray-100 text-gray-600',
  planned: 'bg-amber-100 text-amber-700',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
}

export default function RestorativeChartView({ patientId }: { patientId: string }) {
  const [conditions, setConditions] = useState<Record<string, { condition: string; notes?: string }>>({})
  const [restorations, setRestorations] = useState<Restoration[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authFetch(`/api/v1/restorative/patients/${patientId}/chart`).then(async r => {
      if (r.ok) {
        const d = await r.json()
        setConditions(d.teeth_conditions || {})
        setRestorations(d.restorations || [])
      }
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [patientId])

  if (loading) return <div className="p-8 text-center text-sm text-gray-400">Loading restorative chart...</div>

  // Group restorations by tooth
  const byTooth: Record<number, Restoration[]> = {}
  restorations.forEach(r => {
    if (!byTooth[r.tooth_number]) byTooth[r.tooth_number] = []
    byTooth[r.tooth_number].push(r)
  })

  const hasData = Object.keys(conditions).length > 0 || restorations.length > 0

  return (
    <div className="p-5">
      {!hasData ? (
        <div className="text-center py-12">
          <p className="text-sm text-gray-400 mb-2">No restorative data recorded yet</p>
          <p className="text-xs text-gray-300">Restorative conditions and treatment history will appear here</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Tooth grid — show teeth with data */}
          <div>
            <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2">Tooth Conditions</p>
            <div className="grid grid-cols-8 sm:grid-cols-16 gap-1">
              {Array.from({ length: 32 }, (_, i) => i + 1).map(tooth => {
                const cond = conditions[String(tooth)]
                return (
                  <div
                    key={tooth}
                    className={`w-8 h-8 rounded flex items-center justify-center text-[10px] font-medium border ${
                      cond ? CONDITION_COLORS[cond.condition] || 'bg-gray-50' : 'bg-gray-50 text-gray-300 border-gray-100'
                    }`}
                    title={cond ? `#${tooth}: ${cond.condition}${cond.notes ? ` — ${cond.notes}` : ''}` : `#${tooth}`}
                  >
                    {tooth}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Restoration history */}
          {restorations.length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2">Restorations ({restorations.length})</p>
              <div className="space-y-1.5">
                {restorations.slice(0, 10).map(r => (
                  <div key={r.id} className="flex items-center gap-3 px-3 py-2 bg-gray-50 rounded-lg text-xs">
                    <span className="font-bold text-gray-700 w-6">#{r.tooth_number}</span>
                    {r.surfaces && <span className="text-gray-500">{r.surfaces}</span>}
                    <span className="font-medium text-gray-800">{r.restoration_type}</span>
                    {r.material && <span className="text-gray-400">{r.material}</span>}
                    {r.cdt_code && <span className="text-gray-400 font-mono">{r.cdt_code}</span>}
                    <span className={`ml-auto px-1.5 py-0.5 rounded text-[10px] font-medium ${STATUS_COLORS[r.status] || 'bg-gray-100'}`}>
                      {r.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
