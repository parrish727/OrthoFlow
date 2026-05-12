import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, TrendingUp, TrendingDown, DollarSign, BarChart3, AlertTriangle, Lightbulb, ShieldCheck, HelpCircle } from 'lucide-react'
import { api } from '../lib/api'
import Tooltip from '../components/Tooltip'

// AI-generated insights for demo
const aiInsights = [
  { type: 'anomaly', icon: AlertTriangle, color: 'text-amber-600 bg-amber-50 border-amber-200', title: 'Spend Anomaly Detected', body: 'Ormco Corporation spend is 23% higher than your 3-month average. Last month: $1,950 → This month: $2,450. Review recent orders for accuracy.' },
  { type: 'optimization', icon: DollarSign, color: 'text-emerald-600 bg-emerald-50 border-emerald-200', title: 'Supply Reorder Optimization', body: 'Based on your usage patterns, you order Damon brackets every 3 weeks but consume them in 4. Shifting to monthly orders reduces inventory waste by 25% and frees up $1,200 in working capital. Charlotte-area practices averaging 15% lower supply costs with bulk quarterly ordering.' },
  { type: 'duplicate', icon: ShieldCheck, color: 'text-blue-600 bg-blue-50 border-blue-200', title: '2 Potential Duplicates Caught', body: 'Henry Schein invoice HS-8834 ($1,280) appears similar to HS-8801 ($1,280) from last week. Same vendor, same amount — flagged for review.' },
  { type: 'comparison', icon: Lightbulb, color: 'text-violet-600 bg-violet-50 border-violet-200', title: 'Vendor Price Comparison', body: 'Patterson Dental charges 12% more than Henry Schein for equivalent sterilization supplies. Switching could save ~$180/month.' },
]

const monthlySpend = [
  { month: 'Dec', amount: 28400 },
  { month: 'Jan', amount: 32400 },
  { month: 'Feb', amount: 28900 },
  { month: 'Mar', amount: 35200 },
  { month: 'Apr', amount: 31800 },
  { month: 'May', amount: 29500 },
]

const categoryTrend = [
  { category: 'Supplies', current: 14200, previous: 12800, color: 'bg-blue-500' },
  { category: 'Lab', current: 8900, previous: 9200, color: 'bg-violet-500' },
  { category: 'Equipment', current: 3200, previous: 1800, color: 'bg-emerald-500' },
  { category: 'Invisalign', current: 4800, previous: 4800, color: 'bg-pink-500' },
  { category: 'Services', current: 1200, previous: 1200, color: 'bg-amber-500' },
]

const forecast = {
  currentSpend: 29500,
  projectedMonthly: 31200,
  quarterBudget: 90000,
  projectedQuarter: 93600,
  overBudget: true,
  overAmount: 3600,
}

export default function Analytics() {
  const navigate = useNavigate()
  const [invoices, setInvoices] = useState<{total_amount: number; status: string}[]>([])
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

  const totalSpend = invoices.reduce((s, i) => s + i.total_amount, 0) || 29500
  const maxSpend = Math.max(...monthlySpend.map(m => m.amount))

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center gap-4">
          <button onClick={() => navigate('/')} className="w-8 h-8 bg-gray-100 hover:bg-gray-200 rounded-lg flex items-center justify-center transition-colors">
            <ArrowLeft size={16} className="text-gray-600" />
          </button>
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Analytics & AI Insights</h1>
            <p className="text-xs text-gray-500">Spend intelligence powered by OrthoFlow AI</p>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {loading ? (
          <div className="text-center text-gray-400 py-12 text-sm">Loading...</div>
        ) : (
          <>
            {/* Summary Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-8">
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <DollarSign size={16} className="text-gray-400" />
                  <span className="text-xs text-emerald-600 font-medium flex items-center gap-1"><TrendingDown size={12} /> 7%</span>
                </div>
                <p className="text-2xl font-semibold text-gray-900">${totalSpend.toLocaleString()}</p>
                <p className="text-xs text-gray-500 mt-1">This Month</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <BarChart3 size={16} className="text-gray-400" />
                  <Tooltip content="Average cost to process one invoice through OrthoFlow vs manual ($22 industry avg)"><HelpCircle size={12} className="text-gray-300" /></Tooltip>
                </div>
                <p className="text-2xl font-semibold text-gray-900">$3.20</p>
                <p className="text-xs text-gray-500 mt-1">Cost Per Invoice</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <TrendingUp size={16} className="text-gray-400" />
                </div>
                <p className="text-2xl font-semibold text-emerald-600">$1,840</p>
                <p className="text-xs text-gray-500 mt-1">Savings This Month</p>
              </div>
              <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <ShieldCheck size={16} className="text-gray-400" />
                </div>
                <p className="text-2xl font-semibold text-blue-600">2</p>
                <p className="text-xs text-gray-500 mt-1">Duplicates Caught</p>
              </div>
            </div>

            {/* AI Insights */}
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-4">
                <Lightbulb size={16} className="text-amber-500" />
                <h3 className="text-sm font-semibold text-gray-800">AI Insights</h3>
                <Tooltip content="OrthoFlow AI analyzes your spending patterns and flags anomalies, savings opportunities, and potential issues automatically.">
                  <HelpCircle size={13} className="text-gray-400" />
                </Tooltip>
              </div>
              <div className="space-y-3">
                {aiInsights.map((insight, i) => (
                  <div key={i} className={`flex items-start gap-4 p-4 rounded-xl border ${insight.color}`}>
                    <insight.icon size={18} className="mt-0.5 flex-shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-gray-800">{insight.title}</p>
                      <p className="text-sm text-gray-600 mt-1 leading-relaxed">{insight.body}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 mb-8">
              {/* Monthly Spend Chart */}
              <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
                <h3 className="text-sm font-medium text-gray-800 mb-4">Monthly Spend Trend</h3>
                <div className="flex items-end gap-3 h-40">
                  {monthlySpend.map(m => (
                    <div key={m.month} className="flex-1 flex flex-col items-center gap-2">
                      <p className="text-xs text-gray-500 font-medium">${(m.amount/1000).toFixed(0)}k</p>
                      <div className="w-full rounded-t-lg relative" style={{ height: `${(m.amount / maxSpend) * 100}%`, background: m.month === 'May' ? '#3B82F6' : '#E5E7EB' }} />
                      <span className="text-xs text-gray-500">{m.month}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Budget Forecast */}
              <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-sm font-medium text-gray-800">Quarter Forecast</h3>
                  <Tooltip content="AI projects your quarterly spend based on current trends and seasonal patterns.">
                    <HelpCircle size={13} className="text-gray-400" />
                  </Tooltip>
                </div>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">Projected Quarter Spend</span>
                      <span className="font-semibold text-gray-900">${forecast.projectedQuarter.toLocaleString()}</span>
                    </div>
                    <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-amber-500 rounded-full" style={{ width: `${(forecast.projectedQuarter / forecast.quarterBudget) * 100}%` }} />
                    </div>
                    <div className="flex justify-between text-xs mt-1">
                      <span className="text-gray-400">Budget: ${forecast.quarterBudget.toLocaleString()}</span>
                      <span className="text-amber-600 font-medium">Over by ${forecast.overAmount.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-xs text-amber-700"><strong>AI Recommendation:</strong> Reduce supply orders by 8% or renegotiate Ormco pricing to stay within budget. Consider switching elastic ligatures to American Orthodontics (15% cheaper, same quality rating).</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Category Comparison */}
            <div className="bg-white rounded-2xl border border-gray-200/80 p-6 shadow-sm">
              <h3 className="text-sm font-medium text-gray-800 mb-4">Category Spend — This Month vs Last Month</h3>
              <div className="space-y-4">
                {categoryTrend.map(c => {
                  const change = ((c.current - c.previous) / c.previous * 100).toFixed(0)
                  const isUp = c.current > c.previous
                  return (
                    <div key={c.category}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm text-gray-700">{c.category}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium text-gray-900">${c.current.toLocaleString()}</span>
                          {c.current !== c.previous && (
                            <span className={`text-xs font-medium flex items-center gap-0.5 ${isUp ? 'text-red-500' : 'text-emerald-500'}`}>
                              {isUp ? <TrendingUp size={11} /> : <TrendingDown size={11} />}
                              {isUp ? '+' : ''}{change}%
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${c.color}`} style={{ width: `${(c.current / 15000) * 100}%` }} />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
