import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, Armchair, Stethoscope, CheckCircle2, Loader2, Users } from 'lucide-react'
import { api } from '../lib/api'

interface VisitEntry {
  id: number
  patient_id: number
  patient_name: string
  status: 'waiting' | 'seated' | 'in_treatment' | 'checked_out'
  checked_in_at: string
  status_changed_at: string
}

const STATUS_COLUMNS = [
  {
    key: 'waiting' as const,
    label: 'Waiting',
    icon: Clock,
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    badge: 'bg-amber-100 text-amber-700',
    dot: 'bg-amber-400',
  },
  {
    key: 'seated' as const,
    label: 'Seated',
    icon: Armchair,
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    dot: 'bg-blue-400',
  },
  {
    key: 'in_treatment' as const,
    label: 'In Treatment',
    icon: Stethoscope,
    bg: 'bg-purple-50',
    border: 'border-purple-200',
    badge: 'bg-purple-100 text-purple-700',
    dot: 'bg-purple-400',
  },
  {
    key: 'checked_out' as const,
    label: 'Checked Out',
    icon: CheckCircle2,
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    badge: 'bg-emerald-100 text-emerald-700',
    dot: 'bg-emerald-400',
  },
]

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ${mins % 60}m`
}

export default function VisitTracker() {
  const [visits, setVisits] = useState<VisitEntry[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const loadVisits = useCallback(async () => {
    try {
      const res = await api.request('/api/v1/visit-tracker')
      if (res.ok) {
        const data = await res.json()
        setVisits(data.visits || data || [])
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadVisits()
    const interval = setInterval(loadVisits, 30000)
    return () => clearInterval(interval)
  }, [loadVisits])

  const grouped = STATUS_COLUMNS.map(col => ({
    ...col,
    patients: visits.filter(v => v.status === col.key),
  }))

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-8">
        <div className="flex items-center justify-center gap-2 text-gray-400">
          <Loader2 size={18} className="animate-spin" />
          <span className="text-sm">Loading patient flow...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={16} className="text-teal-600" />
          <h3 className="font-medium text-gray-800">Today's Patient Flow</h3>
        </div>
        <span className="text-xs text-gray-400">
          {visits.length} patient{visits.length !== 1 ? 's' : ''} today
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 divide-x divide-gray-100">
        {grouped.map(col => {
          const Icon = col.icon
          return (
            <div key={col.key} className="min-h-[120px]">
              <div className={`px-3 py-2.5 ${col.bg} border-b ${col.border} flex items-center justify-between`}>
                <div className="flex items-center gap-1.5">
                  <Icon size={14} className={col.badge.split(' ')[1]} />
                  <span className="text-xs font-medium text-gray-700">{col.label}</span>
                </div>
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${col.badge}`}>
                  {col.patients.length}
                </span>
              </div>
              <div className="p-2 space-y-1">
                {col.patients.length === 0 ? (
                  <p className="text-xs text-gray-300 text-center py-4">—</p>
                ) : (
                  col.patients.map(patient => (
                    <button
                      key={patient.id}
                      onClick={() => navigate(`/patients/${patient.patient_id}`)}
                      className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-gray-50 transition-colors group"
                    >
                      <p className="text-sm font-medium text-gray-800 group-hover:text-teal-700 transition-colors truncate">
                        {patient.patient_name}
                      </p>
                      <div className="flex items-center gap-1 mt-0.5">
                        <span className={`w-1.5 h-1.5 rounded-full ${col.dot}`} />
                        <span className="text-xs text-gray-400">
                          {timeAgo(patient.status_changed_at)}
                        </span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
