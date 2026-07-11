import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, Clock, ChevronLeft, ChevronRight, Users, GripVertical, Clipboard, UserMinus, AlertCircle, RotateCw } from 'lucide-react'
import { api } from '../lib/api'

interface Appointment {
  id: string
  patient_id: string
  patient_name: string
  chair_id: string | null
  da_id: string | null
  appointment_date: string
  start_time: string
  end_time: string
  duration_minutes: number
  status: string
  appointment_type: string | null
  notes: string | null
}

interface Chair {
  id: string
  name: string
  color: string | null
  is_active: boolean
  sort_order: number
}

interface DA {
  id: string
  first_name: string
  last_name: string
  color: string | null
}

interface ScheduleColumn {
  chair: Chair
  appointments: Appointment[]
}

interface ScheduleData {
  date: string
  columns: ScheduleColumn[]
  unassigned: Appointment[]
  total_appointments: number
}

const STATUS_COLORS: Record<string, string> = {
  scheduled: 'border-l-blue-400 bg-blue-50/50',
  checked_in: 'border-l-amber-400 bg-amber-50/50',
  in_progress: 'border-l-violet-400 bg-violet-50/50',
  completed: 'border-l-emerald-400 bg-emerald-50/50',
  no_show: 'border-l-red-400 bg-red-50/50',
}

function formatTime(timeStr: string): string {
  const [h, m] = timeStr.split(':')
  const hour = parseInt(h, 10)
  const ampm = hour >= 12 ? 'PM' : 'AM'
  const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${display}:${m} ${ampm}`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

export default function Schedule() {
  const [schedule, setSchedule] = useState<ScheduleData | null>(null)
  const [das, setDas] = useState<DA[]>([])
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(true)
const [expandedAppt, setExpandedAppt] = useState<string | null>(null)
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null)
  const [draggingAppt, setDraggingAppt] = useState<string | null>(null)
  const navigate = useNavigate()
  const loadSchedule = useCallback(async () => {
    setLoading(true)
    const [schedRes, dasRes] = await Promise.all([
      api.getSchedule(selectedDate),
      api.getDentalAssistants(),
    ])
    if (schedRes.ok) setSchedule(await schedRes.json())
    if (dasRes.ok) { const d = await dasRes.json(); setDas(d.dental_assistants || []) }
    setLoading(false)
  }, [selectedDate])

  useEffect(() => { loadSchedule() }, [loadSchedule])

  function shiftDate(days: number) {
    const d = new Date(selectedDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setSelectedDate(d.toISOString().split('T')[0])
  }

  // ── Drag-and-Drop: Appointment → Chair Column ──────────────────────────────

  function handleDragStart(e: React.DragEvent, apptId: string, type: 'appointment') {
    e.dataTransfer.setData('application/json', JSON.stringify({ id: apptId, type }))
    e.dataTransfer.effectAllowed = 'move'
    setDraggingAppt(apptId)
  }

  function handleColumnDragOver(e: React.DragEvent, columnId: string) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(columnId)
  }

  function handleColumnDragLeave() {
    setDragOverColumn(null)
  }

  async function handleColumnDrop(e: React.DragEvent, targetChairId: string | null) {
    e.preventDefault()
    setDragOverColumn(null)
    setDraggingAppt(null)

    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'))
      if (data.type === 'appointment') {
        await api.updateAppointment(data.id, { chair_id: targetChairId })
        await loadSchedule()
      }
    } catch { /* ignore invalid drops */ }
  }

  // ── Drag-and-Drop: DA → Appointment Card ───────────────────────────────────

  function handleDADragStart(e: React.DragEvent, daId: string) {
    e.dataTransfer.setData('application/json', JSON.stringify({ id: daId, type: 'da' }))
    e.dataTransfer.effectAllowed = 'copy'
  }

  async function handleApptDADrop(e: React.DragEvent, apptId: string) {
    e.preventDefault()
    e.stopPropagation()

    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'))
      if (data.type === 'da') {
        await api.updateAppointment(apptId, { da_id: data.id })
        await loadSchedule()
      }
    } catch { /* ignore */ }
  }

  function handleDragEnd() {
    setDraggingAppt(null)
    setDragOverColumn(null)
  }

  return (
    <>
        {/* Date Navigation */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <button onClick={() => shiftDate(-1)} className="p-2 hover:bg-white rounded-lg transition-colors" aria-label="Previous day">
              <ChevronLeft size={20} className="text-gray-600" />
            </button>
            <div className="flex items-center gap-2">
              <Calendar size={18} className="text-gray-500" />
              <h2 className="text-lg font-semibold text-gray-900">{formatDate(selectedDate)}</h2>
            </div>
            <button onClick={() => shiftDate(1)} className="p-2 hover:bg-white rounded-lg transition-colors" aria-label="Next day">
              <ChevronRight size={20} className="text-gray-600" />
            </button>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
              className="px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              Today
            </button>
            <input
              type="date"
              value={selectedDate}
              onChange={e => setSelectedDate(e.target.value)}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg bg-white"
            />
          </div>
        </div>

        {/* DA Roster — draggable DA badges */}
        {das.length > 0 && (
          <div className="mb-4">
            <p className="text-[10px] uppercase text-gray-400 font-medium tracking-wider mb-2">Drag DA to assign</p>
            <div className="flex flex-wrap gap-2">
              {das.map(da => (
                <div
                  key={da.id}
                  draggable
                  onDragStart={e => handleDADragStart(e, da.id)}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg cursor-grab active:cursor-grabbing hover:shadow-sm transition-shadow select-none"
                >
                  <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: da.color || '#8B5CF6' }} />
                  <span className="text-xs font-medium text-gray-700">{da.first_name} {da.last_name[0]}.</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Stats bar */}
        {schedule && (
          <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
            <span>{schedule.total_appointments} appointment{schedule.total_appointments !== 1 ? 's' : ''}</span>
            {schedule.unassigned.length > 0 && (
              <span className="text-amber-600 font-medium">{schedule.unassigned.length} unassigned</span>
            )}
            <span className="text-xs text-gray-400 ml-auto">Drag cards between columns to reassign chairs</span>
          </div>
        )}

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="bg-white rounded-2xl border border-gray-200/80 p-4 animate-pulse">
                <div className="h-5 bg-gray-200 rounded w-24 mb-4" />
                <div className="space-y-3">
                  <div className="h-16 bg-gray-100 rounded-xl" />
                  <div className="h-16 bg-gray-100 rounded-xl" />
                </div>
              </div>
            ))}
          </div>
        ) : schedule ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {/* Chair Columns */}
            {schedule.columns.map(col => (
              <div
                key={col.chair.id}
                onDragOver={e => handleColumnDragOver(e, col.chair.id)}
                onDragLeave={handleColumnDragLeave}
                onDrop={e => handleColumnDrop(e, col.chair.id)}
                className={`bg-white rounded-2xl border shadow-sm overflow-hidden transition-all ${
                  dragOverColumn === col.chair.id
                    ? 'border-blue-400 ring-2 ring-blue-100 scale-[1.01]'
                    : 'border-gray-200/80'
                }`}
              >
                <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: col.chair.color || '#6366f1' }} />
                  <h3 className="text-sm font-semibold text-gray-800">{col.chair.name}</h3>
                  <span className="text-xs text-gray-400 ml-auto">{col.appointments.length}</span>
                </div>
                <div className="p-3 space-y-2 min-h-[200px]">
                  {col.appointments.length === 0 ? (
                    <p className="text-xs text-gray-400 text-center py-8">Drop appointments here</p>
                  ) : (
                    col.appointments.map(appt => (
                      <AppointmentCard
                        key={appt.id}
                        appointment={appt}
                        das={das}
                        expanded={expandedAppt === appt.id}
                        isDragging={draggingAppt === appt.id}
                        onToggle={() => setExpandedAppt(expandedAppt === appt.id ? null : appt.id)}
                        onPatientClick={() => navigate(`/patients/${appt.patient_id}`)}
                        onDragStart={e => handleDragStart(e, appt.id, 'appointment')}
                        onDragEnd={handleDragEnd}
                        onDADrop={e => handleApptDADrop(e, appt.id)}
                        onUpdate={loadSchedule}
                      />
                    ))
                  )}
                </div>
              </div>
            ))}

            {/* Unassigned Column */}
            <div
              onDragOver={e => handleColumnDragOver(e, 'unassigned')}
              onDragLeave={handleColumnDragLeave}
              onDrop={e => handleColumnDrop(e, null)}
              className={`bg-white rounded-2xl border shadow-sm overflow-hidden transition-all ${
                dragOverColumn === 'unassigned'
                  ? 'border-amber-400 ring-2 ring-amber-100 scale-[1.01]'
                  : 'border-amber-200/80'
              }`}
            >
              <div className="px-4 py-3 border-b border-amber-100 flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-amber-400" />
                <h3 className="text-sm font-semibold text-amber-800">Unassigned</h3>
                <span className="text-xs text-amber-500 ml-auto">{schedule.unassigned.length}</span>
              </div>
              <div className="p-3 space-y-2 min-h-[200px]">
                {schedule.unassigned.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-8">Drop here to unassign</p>
                ) : (
                  schedule.unassigned.map(appt => (
                    <AppointmentCard
                      key={appt.id}
                      appointment={appt}
                      das={das}
                      expanded={expandedAppt === appt.id}
                      isDragging={draggingAppt === appt.id}
                      onToggle={() => setExpandedAppt(expandedAppt === appt.id ? null : appt.id)}
                      onPatientClick={() => navigate(`/patients/${appt.patient_id}`)}
                      onDragStart={e => handleDragStart(e, appt.id, 'appointment')}
                      onDragEnd={handleDragEnd}
                      onDADrop={e => handleApptDADrop(e, appt.id)}
                        onUpdate={loadSchedule}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-400">Failed to load schedule</div>
        )}
          </>
  )
}

function AppointmentCard({ appointment, das, expanded, isDragging, onToggle, onPatientClick, onDragStart, onDragEnd, onDADrop, onUpdate }: {
  appointment: Appointment
  das: DA[]
  expanded: boolean
  isDragging: boolean
  onToggle: () => void
  onPatientClick: () => void
  onDragStart: (e: React.DragEvent) => void
  onDragEnd: () => void
  onDADrop: (e: React.DragEvent) => void
  onUpdate: () => void
}) {
  const [daDropHover, setDADropHover] = useState(false)
  const statusClass = STATUS_COLORS[appointment.status] || 'border-l-gray-300 bg-gray-50/50'
  const assignedDA = das.find(d => d.id === appointment.da_id)

  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      onDragOver={e => { e.preventDefault(); e.stopPropagation(); setDADropHover(true) }}
      onDragLeave={() => setDADropHover(false)}
      onDrop={e => { setDADropHover(false); onDADrop(e) }}
      onClick={onToggle}
      className={`border-l-4 rounded-xl p-3 cursor-grab active:cursor-grabbing transition-all ${statusClass} ${
        isDragging ? 'opacity-40 scale-95' : ''
      } ${daDropHover ? 'ring-2 ring-violet-300 bg-violet-50/30' : 'hover:shadow-sm'}`}
    >
      <div className="flex items-start gap-2">
        <GripVertical size={14} className="text-gray-300 mt-0.5 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between">
            <div className="flex-1 min-w-0">
              <button
                onClick={e => { e.stopPropagation(); onPatientClick() }}
                className="text-sm font-medium text-gray-900 hover:text-blue-600 transition-colors truncate block text-left"
              >
                {appointment.patient_name}
              </button>
              <div className="flex items-center gap-1.5 mt-0.5">
                <Clock size={12} className="text-gray-400" />
                <span className="text-xs text-gray-500">
                  {formatTime(appointment.start_time)} – {formatTime(appointment.end_time)}
                </span>
              </div>
            </div>
            <span className="text-[10px] uppercase font-medium text-gray-400 tracking-wide">
              {appointment.status.replace('_', ' ')}
            </span>
          </div>

          <div className="flex items-center gap-2 mt-1.5">
            {appointment.appointment_type && (
              <span className="text-xs text-gray-500">{appointment.appointment_type}</span>
            )}
            {assignedDA && (
              <span className="flex items-center gap-1 text-[10px] text-gray-500 ml-auto">
                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: assignedDA.color || '#8B5CF6' }} />
                {assignedDA.first_name}
              </span>
            )}
            {!assignedDA && (
              <span className="text-[10px] text-amber-500 ml-auto italic">No DA</span>
            )}
          </div>

          {expanded && (
            <ExpandedCardDetail appointment={appointment} daDropHover={daDropHover} onUpdate={onUpdate} />
          )}
        </div>
      </div>
    </div>
  )
}

function ExpandedCardDetail({ appointment, daDropHover, onUpdate }: { appointment: Appointment; daDropHover: boolean; onUpdate: () => void }) {
  const [prepBrief, setPrepBrief] = useState<{ today_expected: string; prep_items: string[] } | null>(null)
  const [loadingPrep, setLoadingPrep] = useState(false)
  const [showReschedule, setShowReschedule] = useState(false)
  const [newTime, setNewTime] = useState(appointment.start_time.slice(0, 5))
  const [saving, setSaving] = useState(false)

  async function handleLoadPrep(e: React.MouseEvent) {
    e.stopPropagation()
    if (prepBrief || loadingPrep) return
    setLoadingPrep(true)
    const res = await api.aiPrepBrief(appointment.id)
    if (res.ok) {
      const data = await res.json()
      setPrepBrief({ today_expected: data.today_expected, prep_items: data.prep_items })
    }
    setLoadingPrep(false)
  }

  async function handleUnassignDA(e: React.MouseEvent) {
    e.stopPropagation()
    await api.updateAppointment(appointment.id, { da_id: null })
    onUpdate()
  }

  async function handleMarkLate(e: React.MouseEvent) {
    e.stopPropagation()
    await api.updateAppointment(appointment.id, { status: 'no_show' })
    onUpdate()
  }

  async function handleReschedule(e: React.MouseEvent) {
    e.stopPropagation()
    setSaving(true)
    const [h, m] = newTime.split(':').map(Number)
    const duration = appointment.duration_minutes
    const endH = h + Math.floor((m + duration) / 60)
    const endM = (m + duration) % 60
    const endTime = `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}:00`
    await api.updateAppointment(appointment.id, {
      start_time: `${newTime}:00`,
      end_time: endTime,
      status: 'scheduled',
    })
    setSaving(false)
    setShowReschedule(false)
    onUpdate()
  }

  return (
    <div className="mt-2 pt-2 border-t border-gray-200/60 space-y-2 text-xs text-gray-500">
      <p><span className="font-medium">Duration:</span> {appointment.duration_minutes} min</p>
      {appointment.notes && <p><span className="font-medium">Notes:</span> {appointment.notes}</p>}
      {daDropHover && <p className="text-violet-600 font-medium">Drop DA here to assign</p>}

      {/* Action buttons */}
      <div className="flex flex-wrap gap-1.5 pt-1">
        {/* Unassign DA */}
        {appointment.da_id && (
          <button
            onClick={handleUnassignDA}
            className="flex items-center gap-1 px-2 py-1 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-md transition-colors"
          >
            <UserMinus size={11} />
            Unassign DA
          </button>
        )}

        {/* Mark Late / No Show */}
        {appointment.status === 'scheduled' && (
          <button
            onClick={handleMarkLate}
            className="flex items-center gap-1 px-2 py-1 bg-red-50 hover:bg-red-100 text-red-600 rounded-md transition-colors"
          >
            <AlertCircle size={11} />
            No Show
          </button>
        )}

        {/* Reschedule */}
        <button
          onClick={(e) => { e.stopPropagation(); setShowReschedule(!showReschedule) }}
          className="flex items-center gap-1 px-2 py-1 bg-amber-50 hover:bg-amber-100 text-amber-600 rounded-md transition-colors"
        >
          <RotateCw size={11} />
          Reschedule
        </button>

        {/* Prep Brief */}
        {!prepBrief && (
          <button
            onClick={handleLoadPrep}
            disabled={loadingPrep}
            className="flex items-center gap-1.5 px-2 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-600 rounded-md transition-colors disabled:opacity-50"
          >
            <Clipboard size={11} />
            {loadingPrep ? 'Loading...' : 'Prep Brief'}
          </button>
        )}
      </div>

      {/* Reschedule time picker */}
      {showReschedule && (
        <div className="flex items-center gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg" onClick={e => e.stopPropagation()}>
          <span className="text-amber-700 font-medium">New time:</span>
          <input
            type="time"
            value={newTime}
            onChange={e => setNewTime(e.target.value)}
            className="px-2 py-1 border border-amber-200 rounded text-xs bg-white"
          />
          <button
            onClick={handleReschedule}
            disabled={saving}
            className="px-2 py-1 bg-amber-500 hover:bg-amber-600 text-white rounded text-xs font-medium disabled:opacity-50"
          >
            {saving ? '...' : 'Move'}
          </button>
        </div>
      )}

      {/* Prep Brief result */}
      {prepBrief && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-2 space-y-1">
          <p className="text-indigo-700 font-medium flex items-center gap-1"><Clipboard size={11} /> Prep Brief</p>
          <p className="text-indigo-600">{prepBrief.today_expected}</p>
          {prepBrief.prep_items.length > 0 && (
            <ul className="text-indigo-500 ml-3 list-disc">
              {prepBrief.prep_items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
