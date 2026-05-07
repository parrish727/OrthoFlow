import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload, FileText, CheckCircle, Clock, AlertCircle, LogOut } from 'lucide-react'
import { api } from '../lib/api'

interface Invoice {
  id: string
  vendor_name: string
  invoice_number: string | null
  total_amount: number
  status: string
  confidence_score: number | null
  created_at: string
}

const STATUS_CONFIG: Record<string, { color: string; icon: typeof Clock; label: string }> = {
  pending: { color: 'bg-yellow-100 text-yellow-700', icon: Clock, label: 'Pending' },
  processing: { color: 'bg-blue-100 text-blue-700', icon: Clock, label: 'Processing' },
  coded: { color: 'bg-purple-100 text-purple-700', icon: FileText, label: 'Ready for Review' },
  review: { color: 'bg-orange-100 text-orange-700', icon: AlertCircle, label: 'Needs Review' },
  approved: { color: 'bg-green-100 text-green-700', icon: CheckCircle, label: 'Approved' },
  paid: { color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle, label: 'Paid' },
  rejected: { color: 'bg-red-100 text-red-700', icon: AlertCircle, label: 'Rejected' },
}

export default function Dashboard() {
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const navigate = useNavigate()

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">OrthoFlow AI</h1>
            <p className="text-sm text-gray-500">Accounts Payable Dashboard</p>
          </div>
          <button
            onClick={() => { localStorage.clear(); navigate('/login') }}
            className="flex items-center gap-2 text-gray-500 hover:text-gray-700 text-sm"
          >
            <LogOut size={16} /> Sign Out
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatCard label="Total Invoices" value={stats.total} />
          <StatCard label="Pending Review" value={stats.pending} color="text-yellow-600" />
          <StatCard label="Approved" value={stats.approved} color="text-green-600" />
          <StatCard label="Total Amount" value={`$${stats.totalAmount.toLocaleString()}`} color="text-blue-600" />
        </div>

        {/* Upload Zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center mb-8 transition-colors ${
            dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
          }`}
        >
          <Upload className="mx-auto mb-3 text-gray-400" size={32} />
          <p className="text-gray-600 font-medium">
            {uploading ? 'Uploading...' : 'Drop invoices here or click to upload'}
          </p>
          <p className="text-gray-400 text-sm mt-1">PDF, PNG, JPG — AI will extract and classify automatically</p>
          <input
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg"
            onChange={e => handleUpload(e.target.files)}
            className="hidden"
            id="file-upload"
          />
          <label
            htmlFor="file-upload"
            className="inline-block mt-4 px-6 py-2 bg-blue-600 text-white rounded-lg cursor-pointer hover:bg-blue-700 text-sm font-medium"
          >
            Select Files
          </label>
        </div>

        {/* Invoice Queue */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h2 className="font-semibold text-gray-800">Invoice Queue</h2>
          </div>
          {invoices.length === 0 ? (
            <div className="px-6 py-12 text-center text-gray-400">
              <FileText className="mx-auto mb-3" size={40} />
              <p>No invoices yet. Upload your first invoice to get started.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {invoices.map(invoice => {
                const config = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending
                const Icon = config.icon
                return (
                  <div
                    key={invoice.id}
                    onClick={() => navigate(`/invoice/${invoice.id}`)}
                    className="px-6 py-4 flex items-center justify-between hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                        <FileText size={20} className="text-gray-500" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-800">{invoice.vendor_name}</p>
                        <p className="text-sm text-gray-400">
                          {invoice.invoice_number || 'Processing...'} • {new Date(invoice.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <p className="font-semibold text-gray-800">${invoice.total_amount.toLocaleString()}</p>
                      <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium ${config.color}`}>
                        <Icon size={12} /> {config.label}
                      </span>
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

function StatCard({ label, value, color = 'text-gray-900' }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <p className="text-sm text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  )
}
