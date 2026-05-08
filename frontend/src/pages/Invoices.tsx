import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, FileText, CheckCircle, Clock, AlertCircle, Search, Filter } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { HelpCircle } from 'lucide-react'

const demoInvoices = [
  { id: '1', vendor: 'Ormco Corporation', number: 'INV-2026-4521', amount: 2450, status: 'approved', date: '2026-05-05', category: 'Supplies' },
  { id: '2', vendor: 'Henry Schein Dental', number: 'INV-2026-8834', amount: 1280, status: 'coded', date: '2026-05-06', category: 'Supplies' },
  { id: '3', vendor: 'Precision Dental Lab', number: 'PL-0892', amount: 3200, status: 'approved', date: '2026-05-04', category: 'Lab' },
  { id: '4', vendor: 'Patterson Dental', number: 'PD-112233', amount: 890, status: 'review', date: '2026-05-07', category: 'Equipment' },
  { id: '5', vendor: 'DentalXChange', number: 'DX-2026-05', amount: 149, status: 'paid', date: '2026-05-01', category: 'Insurance' },
  { id: '6', vendor: 'American Orthodontics', number: 'AO-77412', amount: 1750, status: 'approved', date: '2026-05-03', category: 'Supplies' },
  { id: '7', vendor: 'Rocky Mountain Ortho', number: 'RMO-5543', amount: 620, status: 'pending', date: '2026-05-07', category: 'Supplies' },
  { id: '8', vendor: '3M Unitek', number: '3M-2026-1192', amount: 3100, status: 'approved', date: '2026-05-02', category: 'Supplies' },
  { id: '9', vendor: 'CLT Office Cleaning', number: 'CLT-MAY26', amount: 450, status: 'paid', date: '2026-05-01', category: 'Services' },
  { id: '10', vendor: 'Carestream Dental', number: 'CS-REP-441', amount: 1800, status: 'review', date: '2026-05-06', category: 'Equipment' },
]

const STATUS_CONFIG: Record<string, { color: string; bg: string; icon: typeof Clock; label: string }> = {
  pending: { color: 'text-amber-700', bg: 'bg-amber-50 border-amber-200', icon: Clock, label: 'Pending' },
  processing: { color: 'text-blue-700', bg: 'bg-blue-50 border-blue-200', icon: Clock, label: 'Processing' },
  coded: { color: 'text-violet-700', bg: 'bg-violet-50 border-violet-200', icon: FileText, label: 'Ready to Review' },
  review: { color: 'text-orange-700', bg: 'bg-orange-50 border-orange-200', icon: AlertCircle, label: 'Needs Review' },
  approved: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Approved' },
  paid: { color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-200', icon: CheckCircle, label: 'Paid' },
}

export default function Invoices() {
  const navigate = useNavigate()
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  const filtered = demoInvoices.filter(i => {
    if (filter !== 'all' && i.status !== filter) return false
    if (search && !i.vendor.toLowerCase().includes(search.toLowerCase()) && !i.number.toLowerCase().includes(search.toLowerCase())) return false
    return true
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
            <p className="text-xs text-gray-500">All invoices across your practice</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Search + Filter */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
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
            <p className="text-sm font-medium text-gray-600">
              Total: ${filtered.reduce((s, i) => s + i.amount, 0).toLocaleString()}
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50/50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Vendor</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Invoice #</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500">Category</th>
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
                      <td className="px-6 py-3.5 text-sm font-medium text-gray-800">{invoice.vendor}</td>
                      <td className="px-6 py-3.5 text-sm text-gray-500">{invoice.number}</td>
                      <td className="px-6 py-3.5">
                        <span className="px-2.5 py-1 bg-gray-100 text-gray-600 text-xs rounded-full font-medium">{invoice.category}</span>
                      </td>
                      <td className="px-6 py-3.5 text-sm text-gray-500">{new Date(invoice.date).toLocaleDateString()}</td>
                      <td className="px-6 py-3.5 text-sm font-semibold text-gray-800 text-right">${invoice.amount.toLocaleString()}</td>
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
        </div>
      </main>
    </div>
  )
}
