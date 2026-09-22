import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Sparkles, Check, X, Maximize2, Minimize2, CalendarDays, Loader2 } from 'lucide-react'
import { api } from '../lib/api'
import { localToday } from '../lib/dates'

interface DaySummary { date: string; total: number; completed: number }
interface AISuggestion { type: string; message: string; heavy_days: string[]; avg_per_day: number }
interface DayAppt {
  id: string
  start_time?: string
  patient_id?: string
  patient_name?: string
  appointment_type?: string | null
  status?: string
  is_consult?: boolean
  is_medicaid?: boolean
  owes_money?: boolean
}

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// Dashboard monthly calendar. Replaces "Today's Huddle". Shows each day's appointment load and
// what OrthoFlow completed automatically, with an AI-suggested optimization the doctor can accept
// or dismiss (never auto-applied). Resizable (compact/expanded) so the doctor structures the month
// how they want.
export default function MonthlyCalendar() {
  const navigate = useNavigate()
  const today = localToday()
  const [cursor, setCursor] = useState(() => { const [y, m] = today.split('-').map(Number); return { year: y, month: m } })
  const [days, setDays] = useState<Record<string, DaySummary>>({})
  const [suggestion, setSuggestion] = useState<AISuggestion | null>(null)
  const [suggestionAccepted, setSuggestionAccepted] = useState<boolean | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [dayAppts, setDayAppts] = useState<DayAppt[]>([])
  const [dayLoading, setDayLoading] = useState(false)

  const load = useCallback(async () => {
    const res = await api.getScheduleMonth(cursor.year, cursor.month)
    if (res.ok) {
      const d = await res.json()
      setDays(d.days || {})
      setSuggestion(d.ai_suggestion || null)
      setSuggestionAccepted(null)
    }
  }, [cursor])

  useEffect(() => { load() }, [load])

  // Click a day → expand a short in-place view of what's happening that day.
  async function selectDay(ds: string) {
    if (selectedDay === ds) { setSelectedDay(null); return }
    setSelectedDay(ds)
    setDayLoading(true)
    setDayAppts([])
    try {
      const res = await api.getSchedule(ds)
      if (res.ok) {
        const d = await res.json()
        const cols = d.columns || []
        const appts: DayAppt[] = cols.length
          ? cols.flatMap((c: { appointments?: DayAppt[] }) => c.appointments || [])
          : (d.appointments || [])
        appts.sort((a, b) => (a.start_time || '').localeCompare(b.start_time || ''))
        setDayAppts(appts)
      }
    } catch { /* ignore */ }
    setDayLoading(false)
  }

  function shiftMonth(delta: number) {
    setCursor(c => {
      let m = c.month + delta, y = c.year
      if (m < 1) { m = 12; y-- } else if (m > 12) { m = 1; y++ }
      return { year: y, month: m }
    })
  }

  // Build the calendar grid (leading blanks + days of month).
  const firstDow = new Date(cursor.year, cursor.month - 1, 1).getDay()
  const daysInMonth = new Date(cursor.year, cursor.month, 0).getDate()
  const cells: (number | null)[] = [...Array(firstDow).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)]
  const isHeavy = (dateStr: string) => suggestion?.heavy_days?.includes(dateStr)

  function dateStr(day: number) {
    return `${cursor.year}-${String(cursor.month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="monthly-calendar">
      <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
        <CalendarDays size={16} className="text-teal-600" />
        <h3 className="font-medium text-gray-800">Monthly Calendar</h3>
        <div className="flex items-center gap-1 ml-2">
          <button onClick={() => shiftMonth(-1)} aria-label="Previous month" className="p-1 hover:bg-gray-100 rounded"><ChevronLeft size={16} className="text-gray-500" /></button>
          <span className="text-sm font-medium text-gray-700 w-36 text-center">{MONTHS[cursor.month - 1]} {cursor.year}</span>
          <button onClick={() => shiftMonth(1)} aria-label="Next month" className="p-1 hover:bg-gray-100 rounded"><ChevronRight size={16} className="text-gray-500" /></button>
        </div>
        <button data-testid="calendar-resize" onClick={() => setExpanded(e => !e)} className="ml-auto p-1.5 hover:bg-gray-100 rounded text-gray-500" aria-label="Resize calendar">
          {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
        </button>
      </div>

      {/* AI optimization suggestion — doctor accepts or dismisses (never auto-applied) */}
      {suggestion && suggestionAccepted === null && (
        <div className="mx-4 mt-3 flex items-start gap-2 bg-violet-50 border border-violet-100 rounded-xl px-3 py-2.5" data-testid="calendar-ai-suggestion">
          <Sparkles size={15} className="text-violet-500 mt-0.5 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-violet-800">{suggestion.message}</p>
            <p className="text-[10px] text-violet-500 mt-0.5">Heavy days: {suggestion.heavy_days.join(', ')} · avg {suggestion.avg_per_day}/day</p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button data-testid="ai-suggestion-accept" onClick={() => setSuggestionAccepted(true)} className="flex items-center gap-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded px-2 py-1 hover:bg-emerald-100"><Check size={11} /> Apply</button>
            <button data-testid="ai-suggestion-dismiss" onClick={() => setSuggestionAccepted(false)} className="flex items-center gap-1 text-[11px] font-medium text-gray-600 bg-white border border-gray-200 rounded px-2 py-1 hover:bg-gray-50"><X size={11} /> Dismiss</button>
          </div>
        </div>
      )}
      {suggestionAccepted !== null && (
        <p className="mx-4 mt-3 text-[11px] text-gray-400">{suggestionAccepted ? 'Suggestion noted — adjust days by dragging appointments in the Schedule (doctor override).' : 'Suggestion dismissed.'}</p>
      )}

      <div className="p-4">
        <div className="grid grid-cols-7 gap-1 mb-1">
          {DOW.map(d => <div key={d} className="text-center text-[10px] font-semibold text-gray-400 uppercase tracking-wider py-1">{d}</div>)}
        </div>
        <div className="grid grid-cols-7 gap-1">
          {cells.map((day, i) => {
            if (day === null) return <div key={`b${i}`} />
            const ds = dateStr(day)
            const summary = days[ds]
            const isToday = ds === today
            return (
              <button
                key={ds}
                data-testid={`calendar-day-${ds}`}
                onClick={() => selectDay(ds)}
                className={`text-left rounded-lg border p-1.5 transition-colors ${expanded ? 'min-h-[68px]' : 'min-h-[40px]'} ${
                  selectedDay === ds ? 'border-teal-500 bg-teal-50 ring-2 ring-teal-200'
                  : isToday ? 'border-teal-400 bg-teal-50/50' : 'border-gray-100 hover:border-teal-200 hover:bg-gray-50'
                } ${isHeavy(ds) ? 'ring-1 ring-violet-200' : ''}`}
              >
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-medium ${isToday ? 'text-teal-700' : 'text-gray-700'}`}>{day}</span>
                  {summary && summary.total > 0 && (
                    <span className="text-[9px] font-semibold text-teal-700 bg-teal-100 rounded-full px-1.5">{summary.total}</span>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Inline day expansion — short view of what's happening on the clicked day */}
      {selectedDay && (
        <div className="border-t border-gray-100 bg-gray-50/60 px-5 py-4" data-testid="calendar-day-detail">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-lg font-bold text-gray-900">
              {new Date(selectedDay + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
            </h4>
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium text-gray-700">
                {dayAppts.length} appt{dayAppts.length === 1 ? '' : 's'}
                {(() => { const done = dayAppts.filter(a => a.status === 'completed').length; return done ? ` · ${done} done` : '' })()}
              </span>
              <button onClick={() => navigate('/schedule')} className="text-sm font-semibold text-teal-700 hover:text-teal-800 underline underline-offset-2">Open Schedule →</button>
            </div>
          </div>
          {dayLoading ? (
            <div className="py-4 text-center"><Loader2 size={20} className="animate-spin text-gray-400 mx-auto" /></div>
          ) : dayAppts.length === 0 ? (
            <p className="text-base text-gray-500 py-3">Nothing scheduled this day.</p>
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {dayAppts.map(a => (
                <button
                  key={a.id}
                  data-testid="day-detail-appt"
                  onClick={() => a.patient_id && navigate(`/patients/${a.patient_id}`)}
                  className="w-full flex items-center gap-3 text-left bg-white rounded-xl border-2 border-gray-200 px-4 py-3 hover:border-teal-400 transition-colors"
                >
                  <span className="text-base font-mono font-semibold text-gray-700 w-16 shrink-0">{(a.start_time || '').slice(0, 5)}</span>
                  <span className="text-lg font-semibold text-gray-900 truncate flex-1">{a.patient_name || 'Patient'}</span>
                  {a.is_consult && <span className="text-xs font-semibold px-2 py-1 rounded-full bg-blue-100 text-blue-800">Consult</span>}
                  {a.is_medicaid && <span className="text-xs font-semibold px-2 py-1 rounded-full bg-violet-100 text-violet-800">MC</span>}
                  {a.owes_money && <span className="text-xs font-bold px-2 py-1 rounded-full bg-amber-100 text-amber-800">$</span>}
                  <span className="text-sm font-medium text-gray-600 shrink-0">{a.appointment_type || ''}</span>
                  {a.status === 'completed' && <Check size={18} className="text-emerald-600 shrink-0" strokeWidth={3} />}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
