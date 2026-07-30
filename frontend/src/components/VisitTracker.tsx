import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { CalendarClock, Clock, Armchair, Stethoscope, CheckCircle2, Loader2, Users, GripVertical, LogIn, LogOut } from 'lucide-react'
import { api } from '../lib/api'

interface VisitEntry {
  id: string
  patient_id: string
  patient_name: string | null
  status: 'lobby' | 'seated' | 'checked_out' | 'dismissed'
  chair_id: string | null
  checked_in_at: string | null
  seated_at: string | null
  checked_out_at: string | null
  created_at: string
}

interface ScheduledPatient {
  id: string
  patient_id: string
  patient_name: string
  start_time: string
  appointment_type: string | null
  status: string
}

const FLOW_COLUMNS = [
  {
    key: 'lobby' as const,
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
    key: 'checked_out' as const,
    label: 'Checked Out',
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
    key: 'dismissed' as const,
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

function formatTime(timeStr: string): string {
  const [h, m] = timeStr.split(':')
  const hour = parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${display}:${m} ${ampm}`
}

export default function VisitTracker() {
  const [visits, setVisits] = useState<VisitEntry[]>([])
  const [scheduled, setScheduled] = useState<ScheduledPatient[]>([])
  const [loading, setLoading] = useState(true)
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null)
  const [draggingVisit, setDraggingVisit] = useState<string | null>(null)
  const navigate = useNavigate()

  const loadData = useCallback(async () => {
    try {
      // Load visit tracker (patients in flow)
      const visitRes = await api.request('/api/v1/visit-tracker')
      if (visitRes.ok) {
        const data = await visitRes.json()
        setVisits(data.visits || data || [])
      }

      // Load today's schedule to get "Scheduled" patients (not yet checked in)
      const today = new Date().toISOString().split('T')[0]
      const schedRes = await api.getSchedule(today)
      if (schedRes.ok) {
        const schedData = await schedRes.json()
        // Flatten all appointments from all columns + unassigned
        const allAppts: ScheduledPatient[] = []
        for (const col of schedData.columns || []) {
          for (const appt of col.appointments || []) {
            allAppts.push({
              id: appt.id,
              patient_id: appt.patient_id,
              patient_name: appt.patient_name,
              start_time: appt.start_time,
              appointment_type: appt.appointment_type,
              status: appt.status,
            })
          }
        }
        for (const appt of schedData.unassigned || []) {
          allAppts.push({
            id: appt.id,
            patient_id: appt.patient_id,
            patient_name: appt.patient_name,
            start_time: appt.start_time,
            appointment_type: appt.appointment_type,
            status: appt.status,
          })
        }
        setScheduled(allAppts)
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [loadData])

  // Filter scheduled patients: only show those NOT already in the visit tracker
  const checkedInPatientIds = new Set(visits.map(v => v.patient_id))
  const notYetArrived = scheduled.filter(
    s => !checkedInPatientIds.has(s.patient_id) && s.status === 'scheduled'
  )

  // ── Check In Patient (move from Scheduled → Lobby) ─────────────────────────

  async function handleCheckIn(appointmentId: string, patientId: string) {
    try {
      await api.request('/api/v1/visit-tracker', {
        method: 'POST',
        body: JSON.stringify({ patient_id: patientId, appointment_id: appointmentId }),
      })
      await loadData()
    } catch { /* silent */ }
  }

  // ── Dismiss Patient (quick action) ─────────────────────────────────────────

  async function handleDismiss(visitId: string) {
    try {
      await api.request(`/api/v1/visit-tracker/${visitId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'dismissed' }),
      })
      await loadData()
    } catch { /* silent */ }
  }

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
      const visit = visits.find(v => v.id === visitId)
      if (!visit || visit.status === targetStatus) return

      await api.request(`/api/v1/visit-tracker/${visitId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status: targetStatus }),
      })
      await loadData()
    } catch { /* silent */ }
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  const grouped = FLOW_COLUMNS.map(col => ({
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
          {scheduled.length} scheduled · {visits.length} in flow · Drag to advance
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-0 divide-x divide-gray-100">
        {/* ── SCHEDULED COLUMN (not yet arrived) ──────────────────────────── */}
        <div className="min-h-[180px]">
          <div className="px-3 py-2.5 bg-gray-50 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <CalendarClock size={14} className="text-gray-500" />
              <span className="text-xs font-medium text-gray-700">Scheduled</span>
            </div>
            <span className="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-600">
              {notYetArrived.length}
            </span>
          </div>
          <div className="p-2 space-y-1.5">
            {notYetArrived.length === 0 ? (
              <p className="text-xs text-gray-300 text-center py-6">All patients arrived</p>
            ) : (
              notYetArrived.map(patient => (
                <div
                  key={patient.id}
                  className="border-l-[3px] border-l-gray-300 bg-gray-50/50 rounded-lg px-3 py-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <button
                        onClick={() => navigate(`/patients/${patient.patient_id}`)}
                        className="text-sm font-medium text-gray-800 hover:text-teal-700 transition-colors truncate block text-left"
                      >
                        {patient.patient_name}
                      </button>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-gray-400">{formatTime(patient.start_time)}</span>
                        {patient.appointment_type && (
                          <span className="text-[10px] text-gray-400">· {patient.appointment_type}</span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => handleCheckIn(patient.id, patient.patient_id)}
                      className="flex items-center gap-1 px-2 py-1 text-[10px] font-medium text-teal-700 bg-teal-50 hover:bg-teal-100 rounded transition-colors flex-shrink-0"
                      title="Check In"
                    >
                      <LogIn size={10} />
                      Check In
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* ── FLOW COLUMNS (Lobby → Seated → Checkout → Dismissed) ────────── */}
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
                        {/* Quick dismiss button for Lobby/Seated/Checkout */}
                        {col.key !== 'dismissed' && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDismiss(patient.id) }}
                            className="flex items-center gap-0.5 px-1.5 py-0.5 text-[9px] font-medium text-red-600 hover:bg-red-50 rounded transition-colors flex-shrink-0"
                            title="Dismiss patient"
                          >
                            <LogOut size={9} />
                            Dismiss
                          </button>
                        )}
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
