import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, CheckCircle, Clock, AlertCircle, LogOut, HelpCircle, DollarSign, Inbox, ChevronDown, LayoutDashboard, Receipt, BarChart3, Settings, User } from 'lucide-react'
import { api } from '../lib/api'
import Tooltip from '../components/Tooltip'

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
  const navigate = useNavigate()

  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const loadInvoices = useCallback(async () => {
    const res = await api.getInvoices()
    if (res.ok) {
      const data = await res.json()
      setInvoices(data.invoices)
    }
  }, [])

  useEffect(() => { loadInvoices() }, [loadInvoices])

  async function handleUpload(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    for (const file of Array.from(files)) {
      await api.uploadInvoice(file)
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
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <FileText size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">OrthoFlow</h1>
              <p className="text-xs text-gray-500">Accounts Payable</p>
            </div>
          </div>

          {/* Navigation Dropdown */}
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

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Welcome + Stats */}
        <div className="mb-8">
          <h2 className="text-2xl font-semibold text-gray-900 mb-1">Good {new Date().getHours() < 12 ? 'morning' : 'afternoon'}</h2>
          <p className="text-gray-500 text-sm">Here's your accounts payable overview</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard icon={Inbox} label="Total Invoices" value={stats.total} tooltip="All invoices submitted to OrthoFlow" />
          <StatCard icon={Clock} label="Awaiting Action" value={stats.pending} color="text-amber-600" tooltip="Invoices that need your review or are being processed by AI" />
          <StatCard icon={CheckCircle} label="Approved" value={stats.approved} color="text-emerald-600" tooltip="Invoices you've approved — these sync to QuickBooks" />
          <StatCard icon={DollarSign} label="Total Amount" value={`$${stats.totalAmount.toLocaleString()}`} color="text-blue-600" tooltip="Sum of all invoice amounts in the system" />
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
            <label htmlFor="file-upload" className="inline-block px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-full cursor-pointer text-sm font-medium transition-colors shadow-sm">
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
                    className="px-6 py-4 flex items-center justify-between hover:bg-gray-50/50 cursor-pointer transition-colors group"
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
      </main>
    </div>
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
