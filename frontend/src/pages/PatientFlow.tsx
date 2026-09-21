import { useState } from 'react'
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react'
import VisitTracker from '../components/VisitTracker'
import { localDateStr, localToday } from '../lib/dates'

// Patient Flow — the live visit tracker (lobby / seated / checked-out / dismissed), moved out of
// the Dashboard into its own tab between Dashboard and Schedule.
export default function PatientFlow() {
  const [selectedDate, setSelectedDate] = useState(() => localToday())

  function shiftDate(days: number) {
    const d = new Date(selectedDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setSelectedDate(localDateStr(d))
  }

  function label(dateStr: string) {
    if (dateStr === localToday()) return 'Today'
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  return (
    <div data-testid="patient-flow-page">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Patient Flow</h2>
          <p className="text-sm text-gray-500 mt-0.5">Live visit tracker — lobby, chair, and checkout.</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => shiftDate(-1)} className="p-2 hover:bg-white rounded-lg" aria-label="Previous day"><ChevronLeft size={20} className="text-gray-600" /></button>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-gray-200">
            <Calendar size={16} className="text-gray-500" />
            <span className="text-sm font-medium text-gray-900">{label(selectedDate)}</span>
          </div>
          <button onClick={() => shiftDate(1)} className="p-2 hover:bg-white rounded-lg" aria-label="Next day"><ChevronRight size={20} className="text-gray-600" /></button>
        </div>
      </div>
      <VisitTracker selectedDate={selectedDate} />
    </div>
  )
}
