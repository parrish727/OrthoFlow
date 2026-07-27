import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, Armchair, Stethoscope, CheckCircle2, Loader2, Users, GripVertical } from 'lucide-react'
import { api } from '../lib/api'

interface VisitEntry {
  id: string
  patient_id: string
  patient_name: string | null
  status: 'waiting' | 'seated' | 'in_treatment' | 'checked_out'
  chair_id: string | null
  checked_in_at: string | null
  seated_at: string | null
  checked_out_at: string | null
  created_at: string
}

const STATUS_COLUMNS = [
  {
    key: 'waiting' as const,
    label: 'Lobby',
    icon: Clock,
    headerBg: 'bg-amber-50',
    headerBorder: 'border-amber-200',
    badge: 'bg-amber-100 text-amber-700',
    dot: 'bg-amber-400',
    cardBorder: 'border-l-amber-400',
    cardBg: 'bg-amber-50/50',
    dropActive: 'border-amber-400 ring-2 ring-amber-100',
  },
  {
    key: 'seated' as const,
    label: 'Seated',
    icon: Armchair,
    headerBg: 'bg-blue-50',
    headerBorder: 'border-blue-200',
    badge: 'bg-blue-100 text-blue-700',
    dot: 'bg-blue-400',
    cardBorder: 'border-l-blue-400',
    cardBg: 'bg-blue-50/50',
    dropActive: 'border-blue-400 ring-2 ring-blue-100',
  },
  {
    key: 'in_treatment' as const,
    label: 'Checkout',
    icon: Stethoscope,
    headerBg: 'bg-purple-50',
    headerBorder: 'border-purple-200',
    badge: 'bg-purple-100 text-purple-700',
    dot: 'bg-purple-400',
    cardBorder: 'border-l-purple-400',
    cardBg: 'bg-purple-50/50',
    dropActive: 'border-purple-400 ring-2 ring-purple-100',
  },
  {
    key: 'checked_out' as const,
    label: 'Dismissed',
    icon: CheckCircle2,
    headerBg: 'bg-emerald-50',
    headerBorder: 'border-emerald-200',
    badge: 'bg-emerald-100 text-emerald-700',
    dot: 'bg-emerald-400',
    cardBorder: 'border-l-emerald-400',
    cardBg: 'bg-emerald-50/50',
    dropActive: 'border-emerald-400 ring-2 ring-emerald-100',
  },
]

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  return `${hrs}h ${mins % 60}m`
}

export default function VisitTracker() {
  const [visits, setVisits] = useState<VisitEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null)
  const [draggingVisit, setDraggingVisit] = useState<string | null>(null)
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

  // ── Drag-and-Drop Handlers ─────────────────────────────────────────────────

  function handleDragStart(e: React.DragEvent, visitId: string) {
    e.dataTransfer.setData('application/json', JSON.stringify({ id: visitId }))
    e.dataTransfer.effectAllowed = 'move'
    setDraggingVisit(visitId)
  }

  function handleDragEnd() {
    setDraggingVisit(null)
    setDragOverColumn(null)
  }

  function handleColumnDragOver(e: React.DragEvent, columnKey: string) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(columnKey)
  }

  function handleColumnDragLeave() {
    setDragOverColumn(null)
  }

  async function handleColumnDrop(e: React.DragEvent, targetStatus: string) {
    e.preventDefault()
    setDragOverColumn(null)
    setDraggingVisit(null)

    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'))
      const visitId = data.id

      // Find the current visit to check if transition is valid
      const visit = visits.find(v => v.id === visitId)
      if (!visit || visit.status === targetStatus) return

      const res = await api.request(`/api/v1/visit-tracker/${visitId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: targetStatus }),
      })
      if (res.ok) {
        await loadVisits()
      }
    } catch {
      // Invalid drop or transition not allowed — silently ignore
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

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
          {visits.length} patient{visits.length !== 1 ? 's' : ''} today · Drag to move between stages
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-0 divide-x divide-gray-100">
        {grouped.map(col => {
          const Icon = col.icon
          const isDropTarget = dragOverColumn === col.key
          return (
            <div
              key={col.key}
              onDragOver={e => handleColumnDragOver(e, col.key)}
              onDragLeave={handleColumnDragLeave}
              onDrop={e => handleColumnDrop(e, col.key)}
              className={`min-h-[180px] transition-all ${
                isDropTarget ? `${col.dropActive} scale-[1.01]` : ''
              }`}
            >
              {/* Column Header */}
              <div className={`px-3 py-2.5 ${col.headerBg} border-b ${col.headerBorder} flex items-center justify-between`}>
                <div className="flex items-center gap-1.5">
                  <Icon size={14} className={col.badge.split(' ')[1]} />
                  <span className="text-xs font-medium text-gray-700">{col.label}</span>
                </div>
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full ${col.badge}`}>
                  {col.patients.length}
                </span>
              </div>

              {/* Patient Cards */}
              <div className="p-2 space-y-1.5">
                {col.patients.length === 0 ? (
                  <p className="text-xs text-gray-300 text-center py-6">
                    {isDropTarget ? 'Drop here' : '—'}
                  </p>
                ) : (
                  col.patients.map(patient => (
                    <div
                      key={patient.id}
                      draggable
                      onDragStart={e => handleDragStart(e, patient.id)}
                      onDragEnd={handleDragEnd}
                      className={`border-l-[3px] ${col.cardBorder} ${col.cardBg} rounded-lg px-3 py-2.5 cursor-grab active:cursor-grabbing select-none transition-all hover:shadow-sm ${
                        draggingVisit === patient.id ? 'opacity-40 scale-95' : ''
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <GripVertical size={14} className="text-gray-300 mt-0.5 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <button
                            onClick={() => navigate(`/patients/${patient.patient_id}`)}
                            className="text-sm font-medium text-gray-800 hover:text-teal-700 transition-colors truncate block text-left"
                          >
                            {patient.patient_name || 'Unknown Patient'}
                          </button>
                          <div className="flex items-center gap-1 mt-0.5">
                            <span className={`w-1.5 h-1.5 rounded-full ${col.dot}`} />
                            <span className="text-[10px] text-gray-400">
                              {timeAgo(patient.seated_at || patient.checked_in_at || patient.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
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
