import { useState, useEffect, useCallback } from 'react'
import { ChevronLeft, ChevronRight, X, CheckCircle2, Clock, Calendar } from 'lucide-react'
import { api } from '../lib/api'

interface ScheduleNextPopupProps {
  patientId: string
  patientName: string
  onClose: () => void
  onScheduled: () => void
}

interface ExistingAppointment {
  id: string
  appointment_date: string
  start_time: string
  end_time: string
  duration_minutes: number
}

const APPOINTMENT_TYPES = [
  'Adjustment',
  'Retainer Check',
  'Records',
  'Bonding',
  'Deband',
  'Observation',
  'Emergency',
]

const DURATION_OPTIONS = [15, 20, 30, 45, 60]

function getWeekStart(date: Date): Date {
  const d = new Date(date)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day // Monday start
  d.setDate(d.getDate() + diff)
  d.setHours(0, 0, 0, 0)
  return d
}

function formatDate(date: Date): string {
  return date.toISOString().split('T')[0]
}

function formatDisplayDate(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function formatDayName(date: Date): string {
  return date.toLocaleDateString('en-US', { weekday: 'short' })
}

function generateTimeSlots(): string[] {
  const slots: string[] = []
  for (let h = 8; h < 17; h++) {
    for (let m = 0; m < 60; m += 15) {
      slots.push(`${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`)
    }
  }
  return slots
}

function formatTime12h(time: string): string {
  const [h, m] = time.split(':').map(Number)
  const suffix = h >= 12 ? 'PM' : 'AM'
  const hour12 = h === 0 ? 12 : h > 12 ? h - 12 : h
  return `${hour12}:${String(m).padStart(2, '0')} ${suffix}`
}

export default function ScheduleNextPopup({ patientId, patientName, onClose, onScheduled }: ScheduleNextPopupProps) {
  const [weekStart, setWeekStart] = useState(() => getWeekStart(new Date()))
  const [bookedSlots, setBookedSlots] = useState<Record<string, Set<string>>>({})
  const [loading, setLoading] = useState(true)
  const [selectedSlot, setSelectedSlot] = useState<{ date: string; time: string } | null>(null)
  const [duration, setDuration] = useState(30)
  const [appointmentType, setAppointmentType] = useState('Adjustment')
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')
  const [nextVisitPlan, setNextVisitPlan] = useState<string | null>(null)

  // Load the DA's Next Visit recommendation for this patient
  useEffect(() => {
    async function loadNextVisitPlan() {
      try {
        const res = await api.getPatientNotes(patientId)
        if (res.ok) {
          const data = await res.json()
          const notes = data.notes || data || []
          const plan = notes.find((n: { note_text: string }) => n.note_text?.startsWith('[NEXT VISIT]'))
          if (plan) {
            setNextVisitPlan(plan.note_text.replace('[NEXT VISIT] ', ''))
            // Pre-fill appointment type from the plan
            const match = plan.note_text.match(/\[NEXT VISIT\]\s*([^—–\-]+)/)
            if (match) setAppointmentType(match[1].trim())
          }
        }
      } catch {}
    }
    loadNextVisitPlan()
  }, [patientId])

  const TIME_SLOTS = generateTimeSlots()

  // Generate days for the week (Mon-Sat)
  const weekDays = Array.from({ length: 6 }, (_, i) => {
    const d = new Date(weekStart)
    d.setDate(d.getDate() + i)
    return d
  })

  const fetchWeekSchedule = useCallback(async () => {
    setLoading(true)
    const booked: Record<string, Set<string>> = {}

    // Fetch schedule for each day of the week
    const promises = weekDays.map(async (day) => {
      const dateStr = formatDate(day)
      try {
        const res = await api.getSchedule(dateStr)
        if (res.ok) {
          const data = await res.json()
          const daySlots = new Set<string>()

          // Collect all booked time slots from columns
          const allAppts: ExistingAppointment[] = [
            ...(data.columns || []).flatMap((col: { appointments: ExistingAppointment[] }) => col.appointments),
            ...(data.unassigned || []),
          ]

          for (const appt of allAppts) {
            // Mark all 15-min slots that this appointment occupies
            const [startH, startM] = appt.start_time.split(':').map(Number)
            const totalMinutes = appt.duration_minutes || 30
            for (let offset = 0; offset < totalMinutes; offset += 15) {
              const slotH = startH + Math.floor((startM + offset) / 60)
              const slotM = (startM + offset) % 60
              if (slotH < 17) {
                daySlots.add(`${String(slotH).padStart(2, '0')}:${String(slotM).padStart(2, '0')}`)
              }
            }
          }

          booked[dateStr] = daySlots
        }
      } catch {
        // If fetch fails, assume no bookings
        booked[formatDate(day)] = new Set()
      }
    })

    await Promise.all(promises)
    setBookedSlots(booked)
    setLoading(false)
  }, [weekStart])

  useEffect(() => {
    fetchWeekSchedule()
  }, [fetchWeekSchedule])

  function shiftWeek(direction: number) {
    const newStart = new Date(weekStart)
    newStart.setDate(newStart.getDate() + direction * 7)
    setWeekStart(newStart)
    setSelectedSlot(null)
  }

  function isSlotBooked(date: Date, time: string): boolean {
    const dateStr = formatDate(date)
    return bookedSlots[dateStr]?.has(time) || false
  }

  function isPast(date: Date, time: string): boolean {
    const now = new Date()
    const [h, m] = time.split(':').map(Number)
    const slotDate = new Date(date)
    slotDate.setHours(h, m, 0, 0)
    return slotDate < now
  }

  async function handleConfirm() {
    if (!selectedSlot) return
    setSubmitting(true)
    setError('')

    const [h, m] = selectedSlot.time.split(':').map(Number)
    const endH = h + Math.floor((m + duration) / 60)
    const endM = (m + duration) % 60
    const endTime = `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}:00`

    // DA creates appointment as 'proposed' — Front Desk can confirm/modify
    // Front Desk and above create as 'scheduled' directly
    const token = localStorage.getItem('token')
    let userRole = ''
    if (token) {
      try {
        const payload = JSON.parse(atob(token.split('.')[1]))
        userRole = payload.role || ''
      } catch {}
    }
    const isProposal = userRole === 'dental_assistant'

    const res = await api.request('/api/v1/appointments', {
      method: 'POST',
      body: JSON.stringify({
        patient_id: patientId,
        appointment_date: selectedSlot.date,
        start_time: `${selectedSlot.time}:00`,
        end_time: endTime,
        duration_minutes: duration,
        appointment_type: appointmentType,
        status: isProposal ? 'proposed' : 'scheduled',
      }),
    })

    if (res.ok) {
      setSuccess(true)
      setTimeout(() => {
        onScheduled()
        onClose()
      }, 1500)
    } else {
      const data = await res.json().catch(() => ({}))
      setError(data.detail || 'Failed to schedule appointment')
    }
    setSubmitting(false)
  }

  // Success overlay
  if (success) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" />
        <div className="relative bg-white rounded-2xl shadow-xl p-8 text-center animate-in fade-in zoom-in">
          <CheckCircle2 size={48} className="text-teal-600 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-900">Appointment Scheduled</h3>
          <p className="text-sm text-gray-500 mt-1">{patientName} — {formatTime12h(selectedSlot!.time)}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-4xl max-h-[90vh] flex flex-col mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Schedule Next Visit</h3>
            <p className="text-sm text-gray-500">{patientName}</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <X size={18} className="text-gray-400" />
          </button>
        </div>

        {/* DA Recommendation Banner */}
        {nextVisitPlan && (
          <div className="mx-6 mt-3 px-4 py-3 bg-teal-50 border border-teal-200 rounded-xl">
            <p className="text-[10px] uppercase font-semibold text-teal-600 tracking-wider mb-1">DA Recommendation</p>
            <p className="text-sm text-teal-900 font-medium">{nextVisitPlan}</p>
          </div>
        )}

        {/* Week Navigation */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-gray-50">
          <button
            onClick={() => shiftWeek(-1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronLeft size={18} className="text-gray-600" />
          </button>
          <div className="flex items-center gap-2">
            <Calendar size={16} className="text-teal-600" />
            <span className="text-sm font-medium text-gray-700">
              {formatDisplayDate(weekDays[0])} — {formatDisplayDate(weekDays[5])}
            </span>
          </div>
          <button
            onClick={() => shiftWeek(1)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronRight size={18} className="text-gray-600" />
          </button>
        </div>

        {/* Grid */}
        <div className="flex-1 overflow-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-teal-600 border-t-transparent" />
            </div>
          ) : (
            <div className="grid grid-cols-[60px_repeat(6,1fr)] gap-0">
              {/* Day headers */}
              <div className="sticky top-0 bg-white z-10" />
              {weekDays.map((day, i) => (
                <div key={i} className="sticky top-0 bg-white z-10 text-center pb-2 border-b border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase">{formatDayName(day)}</p>
                  <p className="text-sm font-semibold text-gray-800">{day.getDate()}</p>
                </div>
              ))}

              {/* Time rows */}
              {TIME_SLOTS.map((time) => (
                <div key={time} className="contents">
                  {/* Time label — show only on the hour */}
                  <div className="flex items-center justify-end pr-2 h-8">
                    {time.endsWith(':00') && (
                      <span className="text-[10px] text-gray-400 font-medium">{formatTime12h(time)}</span>
                    )}
                  </div>

                  {/* Slot cells */}
                  {weekDays.map((day, dayIdx) => {
                    const dateStr = formatDate(day)
                    const booked = isSlotBooked(day, time)
                    const past = isPast(day, time)
                    const isSelected = selectedSlot?.date === dateStr && selectedSlot?.time === time
                    const disabled = booked || past

                    return (
                      <div
                        key={`${dayIdx}-${time}`}
                        onClick={() => !disabled && setSelectedSlot({ date: dateStr, time })}
                        className={`h-8 border border-gray-50 mx-0.5 rounded-sm transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-teal-600 border-teal-600'
                            : disabled
                              ? 'bg-gray-100 cursor-not-allowed'
                              : 'hover:bg-teal-50 hover:border-teal-200'
                        }`}
                        title={disabled ? (booked ? 'Booked' : 'Past') : `${formatDayName(day)} ${day.getDate()} @ ${formatTime12h(time)}`}
                      />
                    )
                  })}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Confirmation Panel */}
        {selectedSlot && (
          <div className="border-t border-gray-100 px-6 py-4 bg-gray-50/50">
            {error && (
              <p className="text-sm text-red-600 mb-3 bg-red-50 px-3 py-2 rounded-lg">{error}</p>
            )}
            <div className="flex flex-wrap items-end gap-4">
              {/* Selected time display */}
              <div className="flex-1 min-w-[200px]">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Selected</p>
                <div className="flex items-center gap-2">
                  <Clock size={14} className="text-teal-600" />
                  <span className="text-sm font-semibold text-gray-900">
                    {new Date(selectedSlot.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                    {' '}at {formatTime12h(selectedSlot.time)}
                  </span>
                </div>
              </div>

              {/* Duration */}
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Duration</label>
                <select
                  value={duration}
                  onChange={(e) => setDuration(Number(e.target.value))}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300"
                >
                  {DURATION_OPTIONS.map((d) => (
                    <option key={d} value={d}>{d} min</option>
                  ))}
                </select>
              </div>

              {/* Appointment Type */}
              <div>
                <label className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1">Type</label>
                <select
                  value={appointmentType}
                  onChange={(e) => setAppointmentType(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm bg-white focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300"
                >
                  {APPOINTMENT_TYPES.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              {/* Confirm */}
              <button
                onClick={handleConfirm}
                disabled={submitting}
                className="px-5 py-2 bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {submitting ? 'Scheduling...' : 'Confirm'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
