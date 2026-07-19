/**
 * Sprint 1 Clinical Enhancements — sub-component rendered inside PatientDetail.
 * Displays: Alerts, General Dentist, Oral Hygiene, Family, Aligners, Elastics.
 */
import { useState, useEffect } from 'react'
import {
  AlertTriangle, Heart, Users, Star, Stethoscope, Activity,
  Plus, X, ChevronDown, ChevronUp,
} from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function authFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('token')
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
}

interface Props {
  patientId: string
}

interface Alert { id: string; alert_type: string; severity: string; title: string; description: string | null; is_active: boolean }
interface Elastic { id: string; elastic_type: string; size: string | null; force: string | null; wear_schedule: string; attachment_from: string | null; attachment_to: string | null; is_active: boolean }
interface Aligner { id: string; brand: string | null; total_trays: number; current_tray: number; status: string; progress_pct: number; start_date: string | null; refinement_number: number }
interface FamilyMember { id: string; first_name: string; last_name: string; relationship: string | null; status: string }

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-amber-100 text-amber-700 border-amber-200',
  low: 'bg-blue-100 text-blue-700 border-blue-200',
}

const WEAR_LABELS: Record<string, string> = {
  day: '☀️ Daytime Only',
  night: '🌙 Nighttime Only',
  full_time: '⏰ Full Time (Day & Night)',
}

export default function ClinicalEnhancements({ patientId }: Props) {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [elastics, setElastics] = useState<Elastic[]>([])
  const [aligners, setAligners] = useState<Aligner[]>([])
  const [family, setFamily] = useState<{ family: { name: string } | null; members: FamilyMember[] }>({ family: null, members: [] })
  const [expanded, setExpanded] = useState(true)

  useEffect(() => {
    if (!patientId) return
    Promise.all([
      authFetch(`/api/v1/patients/${patientId}/alerts`).then(r => r.ok ? r.json() : []),
      authFetch(`/api/v1/patients/${patientId}/elastics`).then(r => r.ok ? r.json() : []),
      authFetch(`/api/v1/patients/${patientId}/aligners`).then(r => r.ok ? r.json() : []),
      authFetch(`/api/v1/patients/${patientId}/family`).then(r => r.ok ? r.json() : { family: null, members: [] }),
    ]).then(([a, e, al, f]) => {
      setAlerts(a)
      setElastics(e)
      setAligners(al)
      setFamily(f)
    })
  }, [patientId])

  const hasContent = alerts.length > 0 || elastics.length > 0 || aligners.length > 0 || family.members.length > 0

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full text-left"
      >
        <h3 className="text-sm font-semibold text-gray-800 flex items-center gap-2">
          <Activity className="h-4 w-4 text-teal-600" />
          Clinical Details
          {alerts.filter(a => a.severity === 'critical' || a.severity === 'high').length > 0 && (
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
          )}
        </h3>
        {expanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="mt-4 space-y-5">
          {/* Alerts */}
          {alerts.length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2 flex items-center gap-1">
                <AlertTriangle className="h-3 w-3" /> Alerts
              </p>
              <div className="space-y-2">
                {alerts.map(alert => (
                  <div key={alert.id} className={`flex items-start gap-2 px-3 py-2 rounded-lg border text-xs ${SEVERITY_COLORS[alert.severity] || 'bg-gray-100'}`}>
                    <span className="font-bold uppercase text-[9px] mt-0.5">{alert.severity}</span>
                    <div className="flex-1">
                      <span className="font-semibold">{alert.title}</span>
                      {alert.description && <p className="text-[11px] opacity-80 mt-0.5">{alert.description}</p>}
                    </div>
                    <span className="text-[9px] opacity-60 capitalize">{alert.alert_type}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Aligners */}
          {aligners.length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2">Aligner Treatment</p>
              {aligners.filter(a => a.status === 'active').map(aligner => (
                <div key={aligner.id} className="bg-gray-50 rounded-lg p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-800">
                      {aligner.brand || 'Clear Aligners'} {aligner.refinement_number > 0 ? `(Refinement #${aligner.refinement_number})` : ''}
                    </span>
                    <span className="text-xs text-teal-700 font-bold">{aligner.current_tray}/{aligner.total_trays}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                    <div className="bg-teal-500 h-2 rounded-full transition-all" style={{ width: `${aligner.progress_pct}%` }} />
                  </div>
                  <p className="text-[10px] text-gray-500">{aligner.progress_pct}% complete</p>
                </div>
              ))}
            </div>
          )}

          {/* Elastics */}
          {elastics.length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2">Active Elastics</p>
              <div className="space-y-2">
                {elastics.map(e => (
                  <div key={e.id} className="bg-gray-50 rounded-lg p-3 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-gray-800">{e.elastic_type}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-teal-100 text-teal-700 font-medium">
                        {WEAR_LABELS[e.wear_schedule] || e.wear_schedule}
                      </span>
                    </div>
                    <div className="mt-1 text-gray-500 flex items-center gap-3">
                      {e.size && <span>Size: {e.size}</span>}
                      {e.force && <span>Force: {e.force}</span>}
                    </div>
                    {(e.attachment_from || e.attachment_to) && (
                      <p className="mt-1 text-gray-400">{e.attachment_from} → {e.attachment_to}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Family */}
          {family.members.length > 0 && (
            <div>
              <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2 flex items-center gap-1">
                <Users className="h-3 w-3" /> Family — {family.family?.name}
              </p>
              <div className="flex flex-wrap gap-2">
                {family.members.map(m => (
                  <a
                    key={m.id}
                    href={`/patients/${m.id}`}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 bg-gray-50 rounded-lg text-xs hover:bg-gray-100 transition-colors"
                  >
                    <span className="font-medium text-gray-800">{m.first_name} {m.last_name}</span>
                    {m.relationship && <span className="text-gray-400">({m.relationship})</span>}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {!hasContent && (
            <p className="text-xs text-gray-400 text-center py-4">No clinical details added yet</p>
          )}
        </div>
      )}
    </div>
  )
}
