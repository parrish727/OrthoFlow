import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, DollarSign, BarChart3, TrendingUp, HelpCircle } from 'lucide-react'
import { api } from '../lib/api'
import Tooltip from '../components/Tooltip'

interface Invoice {
  id: string
  vendor_name: string
  total_amount: number
  status: string
  created_at: string
}

export default function Analytics() {
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getInvoices().then(async res => {
      if (res.ok) {
        const data = await res.json()
        setInvoices(data.invoices)
      }
      setLoading(false)
    })
  }, [])

  const totalSpend = invoices.reduce((s, i) => s + i.total_amount, 0)
  const approvedCount = invoices.filter(i => i.status === 'approved' || i.status === 'paid').length
  const avgPerInvoice = invoices.length > 0 ? totalSpend / invoices.length : 0

  // Group by vendor
  const vendorSpend: Record<string, number> = {}
  invoices.forEach(i => {
    vendorSpend[i.vendor_name] = (vendorSpend[i.vendor_name] || 0) + i.total_amount
  })
  const topVendors = Object.entries(vendorSpend)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Analytics</h1>
            <p className="text-xs text-gray-500">Spend reports & trends for your practice</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center text-gray-400 py-12 text-sm">Loading...</div>
        ) : invoices.length === 0 ? (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <BarChart3 className="text-gray-300" size={28} />
            </div>
            <p className="text-gray-500 font-medium">No data yet</p>
            <p className="text-gray-400 text-sm mt-1">Analytics will appear here once you start processing invoices</p>
          </div>
        ) : (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <DollarSign size={16} className="text-gray-400" />
                  <Tooltip content="Total amount across all invoices in your account"><HelpCircle size={12} className="text-gray-300" /></Tooltip>
                </div>
                <p className="text-2xl font-semibold text-gray-900">${totalSpend.toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-1">Total Spend</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <BarChart3 size={16} className="text-gray-400" />
                  <Tooltip content="Average dollar amount per invoice"><HelpCircle size={12} className="text-gray-300" /></Tooltip>
                </div>
                <p className="text-2xl font-semibold text-gray-900">${avgPerInvoice.toFixed(0)}</p>
                <p className="text-xs text-gray-500 mt-1">Avg Per Invoice</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp size={16} className="text-gray-400" />
                </div>
                <p className="text-2xl font-semibold text-emerald-600">{approvedCount}</p>
                <p className="text-xs text-gray-500 mt-1">Invoices Approved</p>
              </div>
            </div>

            {/* Top Vendors */}
            {topVendors.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100">
                  <h3 className="text-sm font-medium text-gray-800">Top Vendors by Spend</h3>
                </div>
                <div className="divide-y divide-gray-50">
                  {topVendors.map(([vendor, amount]) => (
                    <div key={vendor} className="px-6 py-4 flex items-center justify-between">
                      <p className="text-sm font-medium text-gray-800">{vendor}</p>
                      <p className="text-sm font-semibold text-gray-900">${amount.toLocaleString()}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}
