import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calendar, Clock, ChevronLeft, ChevronRight, ChevronDown, Users, LayoutDashboard, Receipt, BarChart3, Settings, User, LogOut, CalendarDays } from 'lucide-react'
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
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0])
  const [loading, setLoading] = useState(true)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const [expandedAppt, setExpandedAppt] = useState<string | null>(null)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    api.getPractice().then(async res => {
      if (res.ok) { const data = await res.json(); setPracticeName(data.name || 'OrthoFlow'); setPracticeLogo(data.logo_url || '') }
    })
  }, [])

  const loadSchedule = useCallback(async () => {
    setLoading(true)
    const res = await api.getSchedule(selectedDate)
    if (res.ok) {
      const data = await res.json()
      setSchedule(data)
    }
    setLoading(false)
  }, [selectedDate])

  useEffect(() => { loadSchedule() }, [loadSchedule])

  function shiftDate(days: number) {
    const d = new Date(selectedDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setSelectedDate(d.toISOString().split('T')[0])
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {practiceLogo ? (
              <img src={practiceLogo} alt="" className="w-8 h-8 rounded-lg object-contain" />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <CalendarDays size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Schedule Board</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Menu <ChevronDown size={14} className={`transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-gray-200 shadow-lg py-2 z-50">
                  <DropdownItem icon={LayoutDashboard} label="Dashboard" description="Overview & upload" onClick={() => { setMenuOpen(false); navigate('/') }} />
                  <DropdownItem icon={CalendarDays} label="Schedule" description="Daily appointment board" onClick={() => { setMenuOpen(false); navigate('/schedule') }} />
                  <DropdownItem icon={Users} label="Patients" description="Patient records" onClick={() => { setMenuOpen(false); navigate('/patients') }} />
                  <DropdownItem icon={Receipt} label="Invoices" description="View all invoices" onClick={() => { setMenuOpen(false); navigate('/invoices') }} />
                  <DropdownItem icon={BarChart3} label="Analytics" description="Spend reports & trends" onClick={() => { setMenuOpen(false); navigate('/analytics') }} />
                  <DropdownItem icon={Settings} label="Settings" description="Practice & integrations" onClick={() => { setMenuOpen(false); navigate('/settings') }} />
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
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

        {/* Stats bar */}
        {schedule && (
          <div className="flex items-center gap-4 mb-4 text-sm text-gray-500">
            <span>{schedule.total_appointments} appointment{schedule.total_appointments !== 1 ? 's' : ''}</span>
            {schedule.unassigned.length > 0 && (
              <span className="text-amber-600 font-medium">{schedule.unassigned.length} unassigned</span>
            )}
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
              <div key={col.chair.id} className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
                <div className="px-4 py-3 border-b border-gray-100 flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: col.chair.color || '#6366f1' }}
                  />
                  <h3 className="text-sm font-semibold text-gray-800">{col.chair.name}</h3>
                  <span className="text-xs text-gray-400 ml-auto">{col.appointments.length}</span>
                </div>
                <div className="p-3 space-y-2 min-h-[200px]">
                  {col.appointments.length === 0 ? (
                    <p className="text-xs text-gray-400 text-center py-8">No appointments</p>
                  ) : (
                    col.appointments.map(appt => (
                      <AppointmentCard
                        key={appt.id}
                        appointment={appt}
                        expanded={expandedAppt === appt.id}
                        onToggle={() => setExpandedAppt(expandedAppt === appt.id ? null : appt.id)}
                        onPatientClick={() => navigate(`/patients/${appt.patient_id}`)}
                      />
                    ))
                  )}
                </div>
              </div>
            ))}

            {/* Unassigned Column */}
            {schedule.unassigned.length > 0 && (
              <div className="bg-white rounded-2xl border border-amber-200/80 shadow-sm overflow-hidden">
                <div className="px-4 py-3 border-b border-amber-100 flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-amber-400" />
                  <h3 className="text-sm font-semibold text-amber-800">Unassigned</h3>
                  <span className="text-xs text-amber-500 ml-auto">{schedule.unassigned.length}</span>
                </div>
                <div className="p-3 space-y-2">
                  {schedule.unassigned.map(appt => (
                    <AppointmentCard
                      key={appt.id}
                      appointment={appt}
                      expanded={expandedAppt === appt.id}
                      onToggle={() => setExpandedAppt(expandedAppt === appt.id ? null : appt.id)}
                      onPatientClick={() => navigate(`/patients/${appt.patient_id}`)}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-12 text-gray-400">Failed to load schedule</div>
        )}
      </main>
    </div>
  )
}

function AppointmentCard({ appointment, expanded, onToggle, onPatientClick }: {
  appointment: Appointment
  expanded: boolean
  onToggle: () => void
  onPatientClick: () => void
}) {
  const statusClass = STATUS_COLORS[appointment.status] || 'border-l-gray-300 bg-gray-50/50'

  return (
    <div
      className={`border-l-4 rounded-xl p-3 cursor-pointer transition-all hover:shadow-sm ${statusClass}`}
      onClick={onToggle}
    >
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

      {appointment.appointment_type && (
        <p className="text-xs text-gray-500 mt-1">{appointment.appointment_type}</p>
      )}

      {expanded && (
        <div className="mt-2 pt-2 border-t border-gray-200/60 space-y-1 text-xs text-gray-500">
          <p><span className="font-medium">Duration:</span> {appointment.duration_minutes} min</p>
          {appointment.notes && <p><span className="font-medium">Notes:</span> {appointment.notes}</p>}
        </div>
      )}
    </div>
  )
}

function DropdownItem({ icon: Icon, label, description, onClick }: { icon: typeof Clock; label: string; description: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left">
      <Icon size={16} className="text-gray-400 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
    </button>
  )
}
