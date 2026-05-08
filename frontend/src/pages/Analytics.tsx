import { useNavigate } from 'react-router-dom'
import { ArrowLeft, TrendingUp, TrendingDown, DollarSign, BarChart3 } from 'lucide-react'
import Tooltip from '../components/Tooltip'
import { HelpCircle } from 'lucide-react'

const monthlySpend = [
  { month: 'Jan', amount: 32400 },
  { month: 'Feb', amount: 28900 },
  { month: 'Mar', amount: 35200 },
  { month: 'Apr', amount: 31800 },
  { month: 'May', amount: 29500 },
]

const topVendors = [
  { name: 'Ormco Corporation', amount: 18420, category: 'Supplies', change: +5 },
  { name: 'Henry Schein Dental', amount: 12350, category: 'Supplies', change: -3 },
  { name: 'Precision Lab', amount: 8900, category: 'Lab', change: +12 },
  { name: 'Patterson Dental', amount: 6200, category: 'Equipment', change: 0 },
  { name: 'DentalXChange', amount: 1200, category: 'Insurance', change: -8 },
]

const categoryBreakdown = [
  { category: 'Supplies', amount: 34500, percent: 45, color: 'bg-blue-500' },
  { category: 'Lab', amount: 18200, percent: 24, color: 'bg-violet-500' },
  { category: 'Equipment', amount: 12800, percent: 17, color: 'bg-emerald-500' },
  { category: 'Services', amount: 7400, percent: 10, color: 'bg-amber-500' },
  { category: 'Insurance', amount: 3100, percent: 4, color: 'bg-gray-400' },
]

export default function Analytics() {
  const navigate = useNavigate()
  const maxSpend = Math.max(...monthlySpend.map(m => m.amount))

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Analytics</h1>
            <p className="text-xs text-gray-500">Spend reports & trends</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-8">
        {/* Summary Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <DollarSign size={16} className="text-gray-400" />
              <span className="text-xs text-emerald-600 font-medium flex items-center gap-1"><TrendingDown size={12} /> 8% vs last month</span>
            </div>
            <p className="text-2xl font-semibold text-gray-900">$29,500</p>
            <p className="text-xs text-gray-500 mt-1">Total Spend (May)</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <BarChart3 size={16} className="text-gray-400" />
              <Tooltip content="Average cost to process one invoice through OrthoFlow"><HelpCircle size={12} className="text-gray-300" /></Tooltip>
            </div>
            <p className="text-2xl font-semibold text-gray-900">$3.20</p>
            <p className="text-xs text-gray-500 mt-1">Cost Per Invoice</p>
          </div>
          <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp size={16} className="text-gray-400" />
              <Tooltip content="Money saved by catching early-pay discounts and avoiding late fees"><HelpCircle size={12} className="text-gray-300" /></Tooltip>
            </div>
            <p className="text-2xl font-semibold text-emerald-600">$1,840</p>
            <p className="text-xs text-gray-500 mt-1">Savings This Month</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-2 gap-6 mb-8">
          {/* Monthly Spend Chart */}
          <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-800 mb-4">Monthly Spend</h3>
            <div className="flex items-end gap-3 h-40">
              {monthlySpend.map(m => (
                <div key={m.month} className="flex-1 flex flex-col items-center gap-2">
                  <div className="w-full bg-blue-100 rounded-t-lg relative" style={{ height: `${(m.amount / maxSpend) * 100}%` }}>
                    <div className="absolute inset-0 bg-blue-500 rounded-t-lg opacity-80" />
                  </div>
                  <span className="text-xs text-gray-500">{m.month}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Category Breakdown */}
          <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
            <h3 className="text-sm font-medium text-gray-800 mb-4">Spend by Category</h3>
            <div className="space-y-3">
              {categoryBreakdown.map(c => (
                <div key={c.category}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700">{c.category}</span>
                    <span className="text-sm font-medium text-gray-900">${c.amount.toLocaleString()}</span>
                  </div>
                  <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${c.color}`} style={{ width: `${c.percent}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Top Vendors */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-sm font-medium text-gray-800">Top Vendors</h3>
          </div>
          <div className="divide-y divide-gray-50">
            {topVendors.map(v => (
              <div key={v.name} className="px-6 py-4 flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-800">{v.name}</p>
                  <p className="text-xs text-gray-400">{v.category}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900">${v.amount.toLocaleString()}</p>
                  <p className={`text-xs ${v.change > 0 ? 'text-red-500' : v.change < 0 ? 'text-emerald-500' : 'text-gray-400'}`}>
                    {v.change > 0 ? `+${v.change}%` : v.change < 0 ? `${v.change}%` : 'No change'} vs last month
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}
