import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, CheckCircle, Clock, AlertCircle, Search, Filter, HelpCircle } from 'lucide-react'
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

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: typeof Clock; label: string }> = {
  pending: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', icon: Clock, label: 'Pending' },
  processing: { color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: Clock, label: 'Processing' },
  coded: { color: 'text-violet-700', bg: 'bg-violet-50 border-violet-200', icon: FileText, label: 'Ready to Review' },
  review: { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', icon: AlertCircle, label: 'Needs Review' },
  approved: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Approved' },
  paid: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Paid' },
  rejected: { color: 'text-red-700', bg: 'bg-red-50 border-red-200', icon: AlertCircle, label: 'Rejected' },
}

export default function Invoices() {
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'date' | 'vendor' | 'amount'>('date')
  const [view, setView] = useState<'invoices' | 'documents'>('invoices')

  useEffect(() => {
    api.getInvoices().then(async res => {
      if (res.ok) {
        const data = await res.json()
        setInvoices(data.invoices)
      }
      setLoading(false)
    })
  }, [])

  const filtered = invoices.filter(i => {
    if (filter !== 'all' && i.status !== filter) return false
    if (search && !i.vendor_name.toLowerCase().includes(search.toLowerCase()) && !(i.invoice_number || '').toLowerCase().includes(search.toLowerCase())) return false
    return true
  }).sort((a, b) => {
    if (sortBy === 'date') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    if (sortBy === 'vendor') return a.vendor_name.localeCompare(b.vendor_name)
    if (sortBy === 'amount') return b.total_amount - a.total_amount
    return 0
  })

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Invoices</h1>
            <p className="text-xs text-gray-500">All invoices for your practice</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Tab Switcher */}
        <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
          <button onClick={() => setView('invoices')} className={`px-4 py-2 text-xs font-medium rounded-md transition-colors ${view === 'invoices' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Invoices</button>
          <button onClick={() => setView('documents')} className={`px-4 py-2 text-xs font-medium rounded-md transition-colors ${view === 'documents' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Documents</button>
        </div>

        {view === 'documents' ? (
          /* Documents View — clean file list */
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="text-sm font-medium text-gray-800">Uploaded Files</h3>
            </div>
            {loading ? (
              <div className="px-6 py-12 text-center text-gray-400 text-sm">Loading...</div>
            ) : invoices.filter(i => i.invoice_number).length === 0 ? (
              <div className="px-6 py-12 text-center text-gray-400 text-sm">No documents uploaded yet</div>
            ) : (
              <div className="divide-y divide-gray-50">
                {[...invoices].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()).map(inv => (
                  <div key={inv.id} className="px-6 py-3.5 flex items-center justify-between hover:bg-gray-50/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <FileText size={16} className="text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-800">{inv.vendor_name} — {inv.invoice_number || 'Processing'}</p>
                        <p className="text-xs text-gray-400">{new Date(inv.created_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}</p>
                      </div>
                    </div>
                    <button
                      onClick={() => navigate(`/invoice/${inv.id}`)}
                      className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                    >
                      View
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
        <>
        {/* Search + Filter */}
        <div className="flex flex-col gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by vendor or invoice number..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-gray-400" />
            {['all', 'pending', 'coded', 'review', 'approved', 'paid'].map(f => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${filter === f ? 'bg-blue-500 text-white' : 'bg-white text-gray-600 border border-gray-200 hover:bg-gray-50'}`}
              >
                {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as 'date' | 'vendor' | 'amount')}
              className="ml-2 px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-gray-600 border border-gray-200"
            >
              <option value="date">Sort: Newest</option>
              <option value="vendor">Sort: Vendor A-Z</option>
              <option value="amount">Sort: Highest $</option>
            </select>
          </div>
        </div>

        {/* Invoice Table */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-medium text-gray-800">{filtered.length} invoice{filtered.length !== 1 ? 's' : ''}</h3>
              <Tooltip content="Click any invoice to view details, line items, and take action.">
                <HelpCircle size={13} className="text-gray-400" />
              </Tooltip>
            </div>
            {filtered.length > 0 && (
              <p className="text-sm font-medium text-gray-600">
                Total: ${filtered.reduce((s, i) => s + i.total_amount, 0).toLocaleString()}
              </p>
            )}
          </div>

          {loading ? (
            <div className="px-6 py-12 text-center text-gray-400 text-sm">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="text-gray-300" size={28} />
              </div>
              <p className="text-gray-500 font-medium">No invoices found</p>
              <p className="text-gray-400 text-sm mt-1">Upload invoices from the Dashboard to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Vendor</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Invoice #</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Date</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500">Amount</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map(invoice => {
                    const config = STATUS_CONFIG[invoice.status] || STATUS_CONFIG.pending
                    const Icon = config.icon
                    return (
                      <tr key={invoice.id} onClick={() => navigate(`/invoice/${invoice.id}`)} className="hover:bg-gray-50/50 cursor-pointer transition-colors">
                        <td className="px-6 py-3.5 text-sm font-medium text-gray-800">{invoice.vendor_name}</td>
                        <td className="px-6 py-3.5 text-sm text-gray-500">{invoice.invoice_number || '—'}</td>
                        <td className="px-6 py-3.5 text-sm text-gray-500">{new Date(invoice.created_at).toLocaleDateString()}</td>
                        <td className="px-6 py-3.5 text-sm font-semibold text-gray-800 text-right">${invoice.total_amount.toLocaleString()}</td>
                        <td className="px-6 py-3.5 text-right">
                          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border ${config.bg} ${config.color}`}>
                            <Icon size={11} /> {config.label}
                          </span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        </>
        )}
      </main>
    </div>
  )
}
