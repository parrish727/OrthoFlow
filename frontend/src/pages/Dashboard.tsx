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
        const appointments = data.appointments || data || []
        const notes: ClinicalNote[] = []
        for (const appt of appointments) {
          if (appt.status === 'completed' && appt.notes) {
            notes.push({
              patient_name: appt.patient_name || `${appt.patient_first_name || ''} ${appt.patient_last_name || ''}`.trim(),
              patient_id: appt.patient_id,
              note_preview: (appt.notes || '').slice(0, 100),
              timestamp: appt.end_time || appt.start_time || today,
            })
          }
        }
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900 mb-1">Good {new Date().getHours() < 12 ? 'morning' : 'afternoon'}</h2>
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

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
        <StatCard icon={Inbox} label="Total Invoices" value={stats.total} tooltip="All invoices submitted to OrthoFlow" />
        <StatCard icon={Clock} label="Awaiting Action" value={stats.pending} color="text-amber-600" tooltip="Invoices that need your review or are being processed by AI" />
        <StatCard icon={CheckCircle} label="Approved" value={stats.approved} color="text-emerald-600" tooltip="Invoices you've approved — these sync to QuickBooks" />
        <StatCard icon={DollarSign} label="Total Amount" value={`$${stats.totalAmount.toLocaleString()}`} color="text-blue-600" tooltip="Sum of all invoice amounts in the system" />
      </div>

      {/* Visit Tracker — Patient Flow */}
      <div className="mb-8">
        <VisitTracker />
      </div>

      {/* Upload Zone */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-3">
          <h3 className="text-sm font-medium text-gray-700">Upload Invoices</h3>
          <Tooltip content="Drop PDF or image files here. AI will automatically extract vendor, amounts, and line items.">
            <HelpCircle size={14} className="text-gray-400 cursor-help" />
          </Tooltip>
        </div>
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 ${
            dragOver ? 'border-blue-400 bg-blue-50/50 scale-[1.01]' : 'border-gray-200 hover:border-gray-300 bg-white'
          }`}
        >
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <Upload className="text-gray-400" size={20} />
          </div>
          <p className="text-gray-700 font-medium text-sm">
            {uploading ? 'Uploading...' : 'Drop invoices here'}
          </p>
          <p className="text-gray-400 text-xs mt-1 mb-4">PDF, PNG, or JPG — AI processes them automatically</p>
          <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg" onChange={e => handleUpload(e.target.files)} className="hidden" id="file-upload" />
          <label htmlFor="file-upload" className="inline-block px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-full cursor-pointer text-sm font-medium transition-colors shadow-sm">
            Choose Files
          </label>
        </div>
      </div>

      {/* Invoice Queue */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="font-medium text-gray-800">Invoice Queue</h3>
            <Tooltip content="All your invoices appear here. Click any invoice to see details, edit classifications, or approve/reject.">
              <HelpCircle size={14} className="text-gray-400 cursor-help" />
            </Tooltip>
          </div>
          <span className="text-xs text-gray-400">{invoices.length} invoice{invoices.length !== 1 ? 's' : ''}</span>
        </div>

        {invoices.length === 0 ? (
          <div className="px-6 py-16 text-center">
            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <FileText className="text-gray-300" size={28} />
            </div>
            <p className="text-gray-500 font-medium">No invoices yet</p>
            <p className="text-gray-400 text-sm mt-1">Upload your first invoice above to get started</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50">
            {invoices.map(invoice => {
              const config = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending
              const Icon = config.icon
              return (
                <div
                  key={invoice.id}
                  onClick={() => navigate(`/invoice/${invoice.id}`)}
                  className="px-4 sm:px-6 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-gray-50/50 cursor-pointer transition-colors group"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 bg-gray-50 group-hover:bg-white rounded-xl flex items-center justify-center transition-colors">
                      <FileText size={18} className="text-gray-400" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-800 text-sm">{invoice.vendor_name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {invoice.invoice_number || 'Processing...'} • {new Date(invoice.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <p className="font-semibold text-gray-800 text-sm">${invoice.total_amount.toLocaleString()}</p>
                    <Tooltip content={config.tooltip}>
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.color}`}>
                        <Icon size={11} /> {config.label}
                      </span>
                    </Tooltip>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Today's Clinical Notes */}
      <div className="mt-8 bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <FileText size={16} className="text-teal-600" />
          <h3 className="font-medium text-gray-800">Today's Clinical Notes</h3>
        </div>
        {notesLoading ? (
          <div className="px-6 py-10 text-center">
            <Loader2 size={20} className="animate-spin text-gray-400 mx-auto" />
            <p className="text-sm text-gray-400 mt-2">Loading notes...</p>
          </div>
        ) : !todaysNotes || todaysNotes.length === 0 ? (
          <div className="px-6 py-10 text-center">
            <FileText size={28} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-400">No clinical notes recorded today</p>
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
