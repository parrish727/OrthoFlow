import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, CheckCircle, Clock, AlertCircle, HelpCircle, DollarSign, Inbox, Loader2, ChevronLeft, ChevronRight, Calendar } from 'lucide-react'
import { api } from '../lib/api'
import Tooltip from '../components/Tooltip'
import VisitTracker from '../components/VisitTracker'

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
  const [selectedDate, setSelectedDate] = useState(() => new Date().toISOString().split('T')[0])
  const navigate = useNavigate()

  function shiftDate(days: number) {
    const d = new Date(selectedDate + 'T00:00:00')
    d.setDate(d.getDate() + days)
    setSelectedDate(d.toISOString().split('T')[0])
  }

  function formatDate(dateStr: string) {
    const d = new Date(dateStr + 'T00:00:00')
    const today = new Date().toISOString().split('T')[0]
    if (dateStr === today) return 'Today'
    const yesterday = new Date(); yesterday.setDate(yesterday.getDate() - 1)
    if (dateStr === yesterday.toISOString().split('T')[0]) return 'Yesterday'
    const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
    if (dateStr === tomorrow.toISOString().split('T')[0]) return 'Tomorrow'
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
      const today = new Date().toISOString().split('T')[0]
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
          {selectedDate !== new Date().toISOString().split('T')[0] && (
            <button
              onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}
              className="px-3 py-1.5 text-xs font-medium text-teal-600 hover:bg-teal-50 rounded-lg transition-colors"
            >
              Today
            </button>
          )}
        </div>
      </div>

      {/* Visit Tracker — Patient Flow */}
      <div className="mb-8">
        <VisitTracker selectedDate={selectedDate} />
      </div>

      {/* Daily Huddle Summary */}
      <div className="mt-8 bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <FileText size={16} className="text-teal-600" />
          <h3 className="font-medium text-gray-800">Today's Huddle</h3>
          <span className="text-xs text-gray-400 ml-auto">{todaysNotes?.length || 0} patients scheduled</span>
        </div>
        {notesLoading ? (
          <div className="px-6 py-10 text-center">
            <Loader2 size={20} className="animate-spin text-gray-400 mx-auto" />
            <p className="text-sm text-gray-400 mt-2">Loading schedule...</p>
          </div>
        ) : !todaysNotes || todaysNotes.length === 0 ? (
          <div className="px-6 py-10 text-center">
            <FileText size={28} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-400">No appointments scheduled today</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {todaysNotes.map((note, idx) => (
              <div key={idx} className="px-6 py-4 flex items-center justify-between gap-4 hover:bg-gray-50/50 transition-colors">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{note.patient_name}</p>
                  <p className="text-xs text-gray-500 mt-0.5 truncate">{note.note_preview || 'No preview available'}</p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {new Date(note.timestamp).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}
                  </p>
                </div>
                <button
                  onClick={() => navigate(`/patients/${note.patient_id}`)}
                  className="text-xs font-medium text-teal-600 hover:text-teal-700 transition-colors whitespace-nowrap"
                >
                  View
                </button>
              </div>
            ))}
          </div>
        )}
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
