import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, CheckCircle, Clock, AlertCircle, HelpCircle, DollarSign, Inbox, Loader2, ChevronLeft, ChevronRight, Calendar, Search } from 'lucide-react'
import { api } from '../lib/api'
import { localDateStr, localToday } from '../lib/dates'
import Tooltip from '../components/Tooltip'
import MonthlyCalendar from '../components/MonthlyCalendar'
import AutomationActivity from '../components/AutomationActivity'
import AIAssist from '../components/AIAssist'

interface Invoice {
  id: string
  vendor_name: string
  invoice_number: string | null
  total_amount: number
  status: string
  confidence_score: number | null
  created_at: string
}

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: typeof Clock; label: string; tooltip: string }> = {
  pending: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', icon: Clock, label: 'Pending', tooltip: 'Invoice received — waiting for AI to process' },
  processing: { color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: Clock, label: 'Processing', tooltip: 'AI is extracting and classifying line items' },
  coded: { color: 'text-violet-700', bg: 'bg-violet-50 border-violet-200', icon: FileText, label: 'Ready to Review', tooltip: 'AI finished — review the classification and approve or reject' },
  review: { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', icon: AlertCircle, label: 'Needs Review', tooltip: 'AI confidence was low — please review manually' },
  approved: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Approved', tooltip: 'Approved and ready to sync to QuickBooks' },
  paid: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Paid', tooltip: 'Payment completed' },
  rejected: { color: 'text-red-700', bg: 'bg-red-50 border-red-200', icon: AlertCircle, label: 'Rejected', tooltip: 'This invoice was rejected and will not be processed' },
}

export default function Dashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [selectedDate, setSelectedDate] = useState(() => localToday())
  const navigate = useNavigate()

  // Patient search / jump bar
  interface PatientHit { id: string; first_name: string; last_name: string; status?: string }
  const [patientQuery, setPatientQuery] = useState('')
  const [patientHits, setPatientHits] = useState<PatientHit[]>([])
  const [searchingPatients, setSearchingPatients] = useState(false)

  useEffect(() => {
    const q = patientQuery.trim()
    if (q.length < 2) { setPatientHits([]); return }
    let active = true
    setSearchingPatients(true)
    const t = setTimeout(async () => {
      try {
        const res = await api.getPatients({ search: q, size: 8 })
        if (res.ok && active) {
          const data = await res.json()
          setPatientHits(data.patients || data.items || [])
        }
      } catch { /* silently handle */ }
      if (active) setSearchingPatients(false)
    }, 250)
    return () => { active = false; clearTimeout(t) }
  }, [patientQuery])

  function shiftDate(days: number) {
    const d = new Date(selectedDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setSelectedDate(localDateStr(d))
  }

  function formatDate(dateStr: string) {
    const d = new Date(dateStr + 'T00:00:00')
    const today = localToday()
    if (dateStr === today) return 'Today'
    const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1)
    if (dateStr === localDateStr(yesterday)) return 'Yesterday'
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
    if (dateStr === localDateStr(tomorrow)) return 'Tomorrow'
    return d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  // Today's Clinical Notes
  interface ClinicalNote {
    patient_name: string
    patient_id: string
    note_preview: string
    timestamp: string
  }
  const [todaysNotes, setTodaysNotes] = useState<ClinicalNote[] | null>(null)
  const [notesLoading, setNotesLoading] = useState(false)

  const loadInvoices = useCallback(async () => {
    try {
      const res = await api.getInvoices()
      if (res.ok) {
        const data = await res.json()
        setInvoices(data.invoices || [])
      }
    } catch {
      // silently handle
    }
  }, [])

  const loadTodaysNotes = useCallback(async () => {
    setNotesLoading(true)
    try {
      const today = localToday()
      const res = await api.getSchedule(today)
      if (res.ok) {
        const data = await res.json()
        // Schedule returns { columns: [{ appointments: [...] }] } structure
        const appointments = data.columns
          ? data.columns.flatMap((col: { appointments: unknown[] }) => col.appointments || [])
          : data.appointments || []
        // Huddle summary: show ALL today's appointments as a preview of the day
        const notes: ClinicalNote[] = []
        for (const appt of appointments) {
          const name = appt.patient_name || `${appt.patient_first_name || ''} ${appt.patient_last_name || ''}`.trim()
          if (!name) continue
          notes.push({
            patient_name: name,
            patient_id: appt.patient_id,
            note_preview: appt.appointment_type
              ? `${appt.appointment_type}${appt.notes ? ' — ' + appt.notes.slice(0, 60) : ''}`
              : appt.notes ? appt.notes.slice(0, 80) : 'Scheduled',
            timestamp: appt.start_time || today,
          })
        }
        // Sort by start time
        notes.sort((a, b) => a.timestamp.localeCompare(b.timestamp))
        setTodaysNotes(notes)
      } else {
        setTodaysNotes([])
      }
    } catch {
      setTodaysNotes([])
    }
    setNotesLoading(false)
  }, [])

  useEffect(() => { loadInvoices(); loadTodaysNotes() }, [loadInvoices, loadTodaysNotes])

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    try {
      for (const file of Array.from(files)) {
        await api.uploadInvoice(file)
      }
    } catch {
      // silently handle
    }
    setUploading(false)
    loadInvoices()
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    handleUpload(e.dataTransfer.files)
  }

  const stats = {
    total: invoices.length,
    pending: invoices.filter(i => ['pending', 'processing', 'coded', 'review'].includes(i.status)).length,
    approved: invoices.filter(i => i.status === 'approved' || i.status === 'paid').length,
    totalAmount: invoices.reduce((sum, i) => sum + i.total_amount, 0),
  }

  return (
    <>
      {/* Welcome + Date Navigation */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-1">Good {new Date().getHours() < 12 ? 'morning' : 'afternoon'}</h2>
          <p className="text-gray-500 text-sm">Here's your practice overview</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => shiftDate(-1)} className="p-2 hover:bg-white rounded-lg transition-colors" aria-label="Previous day">
            <ChevronLeft size={20} className="text-gray-600" />
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-gray-200">
            <Calendar size={16} className="text-gray-500" />
            <span className="text-sm font-medium text-gray-900">{formatDate(selectedDate)}</span>
          </div>
          <button onClick={() => shiftDate(1)} className="p-2 hover:bg-white rounded-lg transition-colors" aria-label="Next day">
            <ChevronRight size={20} className="text-gray-600" />
          </button>
          {selectedDate !== localToday() && (
            <button
              onClick={() => setSelectedDate(localToday())}
              className="px-3 py-1.5 text-xs font-medium text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
            >
              Today
            </button>
          )}
        </div>
      </div>

      {/* Patient search / jump bar */}
      <div className="mb-6 relative" data-testid="dashboard-patient-search">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={patientQuery}
          onChange={e => setPatientQuery(e.target.value)}
          placeholder="Search patients by name..."
          className="w-full pl-9 pr-9 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300"
        />
        {searchingPatients && <Loader2 size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
        {patientHits.length > 0 && (
          <div className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden" data-testid="dashboard-patient-results">
            {patientHits.map(p => (
              <button
                key={p.id}
                data-testid={`dashboard-patient-hit-${p.id}`}
                onClick={() => { setPatientQuery(''); setPatientHits([]); navigate(`/patients/${p.id}`) }}
                className="w-full text-left px-4 py-2.5 text-sm text-gray-800 hover:bg-teal-50 flex items-center justify-between"
              >
                <span>{p.first_name} {p.last_name}</span>
                {p.status && <span className="text-[10px] text-gray-400 capitalize">{p.status.replace('_', ' ')}</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Patients that need attention — surfaced at the top of the Dashboard */}
      <div className="mb-8">
        <AIAssist />
      </div>

      {/* OrthoFlow AI — what it automated */}
      <div className="mb-8">
        <AutomationActivity />
      </div>

      {/* Monthly Calendar — resizable; shows load + what OrthoFlow handled automatically */}
      <div className="mb-8">
        <MonthlyCalendar />
      </div>
    </>
  )
}

function StatCard({ icon: Icon, label, value, color = 'text-gray-900', tooltip }: { icon: typeof Clock; label: string; value: string | number; color?: string; tooltip: string }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <div className="w-8 h-8 bg-gray-50 rounded-lg flex items-center justify-center">
          <Icon size={16} className="text-gray-400" />
        </div>
        <Tooltip content={tooltip}>
          <HelpCircle size={13} className="text-gray-300 cursor-help hover:text-gray-400 transition-colors" />
        </Tooltip>
      </div>
      <p className={`text-2xl font-semibold ${color} tracking-tight`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}
