import { useState, useEffect, useCallback } from 'react'
import { Users, FileText, Download, DollarSign, TrendingUp, Percent, Clock, Filter, PieChart } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../lib/api'

interface ProductionData {
  total_production: number
  total_collections: number
  collection_rate: number
  ar_total: number
  monthly: { month: string; production: number; collections: number; rate: number }[]
}

interface ArAging {
  current: { amount: number; count: number }
  thirty: { amount: number; count: number }
  sixty: { amount: number; count: number }
  ninety: { amount: number; count: number }
  over120: { amount: number; count: number }
}

interface ProviderRow {
  provider_name: string
  total_procedures: number
  avg_per_day: number
  total_amount: number
}

export default function Reports() {
  const [startDate, setStartDate] = useState(() => {
    const d = new Date()
    d.setMonth(d.getMonth() - 6)
    return d.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0])
  const [provider, setProvider] = useState('')
  const [production, setProduction] = useState<ProductionData | null>(null)
  const [arAging, setArAging] = useState<ArAging | null>(null)
  const [providers, setProviders] = useState<ProviderRow[]>([])
  const [loading, setLoading] = useState(true)
  const loadReports = useCallback(async () => {
    setLoading(true)
    const params: Record<string, string> = { start_date: startDate, end_date: endDate }
    if (provider) params.provider = provider

    const [prodRes, arRes, provRes] = await Promise.all([
      api.reportsProduction(params),
      api.reportsArAging(params),
      api.reportsProviderProductivity(params),
    ])

    if (prodRes.ok) setProduction(await prodRes.json())
    if (arRes.ok) setArAging(await arRes.json())
    if (provRes.ok) {
      const data = await provRes.json()
      setProviders(data.providers || [])
    }
    setLoading(false)
  }, [startDate, endDate, provider])

  useEffect(() => { loadReports() }, [loadReports])

  function exportCSV() {
    if (!production) return
    const headers = ['Month', 'Production', 'Collections', 'Rate %']
    const rows = production.monthly.map(m => [m.month, m.production.toFixed(2), m.collections.toFixed(2), m.rate.toFixed(1)])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `orthoflow-report-${startDate}-${endDate}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function fmt(n: number): string {
    return '$' + n.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }

  return (
    <>
        {/* Filters */}
        <div className="flex flex-wrap items-end gap-4 mb-6">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={e => setStartDate(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={e => setEndDate(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Provider</label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 bg-white min-w-[160px]"
            >
              <option value="">All Providers</option>
              {providers.map(p => (
                <option key={p.provider_name} value={p.provider_name}>{p.provider_name}</option>
              ))}
            </select>
          </div>
          <button
            onClick={exportCSV}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 rounded-lg text-sm font-medium text-gray-700 transition-colors ml-auto"
          >
            <Download size={14} /> Export CSV
          </button>
        </div>

        {/* Key Metrics */}
        {production && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
            <MetricCard icon={DollarSign} label="Total Production" value={fmt(production.total_production)} color="text-blue-600" />
            <MetricCard icon={TrendingUp} label="Total Collections" value={fmt(production.total_collections)} color="text-emerald-600" />
            <MetricCard icon={Percent} label="Collection Rate" value={`${production.collection_rate.toFixed(1)}%`} color="text-violet-600" />
            <MetricCard icon={Clock} label="AR Total" value={fmt(production.ar_total)} color="text-amber-600" />
          </div>
        )}

        {/* Production Chart */}
        {production && production.monthly.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 mb-6">
            <h3 className="font-medium text-gray-800 text-sm mb-4">Production vs Collections</h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={production.monthly}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value: number) => ['$' + value.toLocaleString()]} />
                  <Legend />
                  <Bar dataKey="production" fill="#3b82f6" name="Production" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="collections" fill="#10b981" name="Collections" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Collections vs Production Table */}
        {production && production.monthly.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-medium text-gray-800 text-sm">Monthly Breakdown</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/50">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Month</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Production</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Collections</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Rate %</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {production.monthly.map((m, i) => (
                    <tr key={i} className="hover:bg-gray-50/50">
                      <td className="px-6 py-3 font-medium text-gray-700">{m.month}</td>
                      <td className="px-6 py-3 text-right text-gray-700">{fmt(m.production)}</td>
                      <td className="px-6 py-3 text-right text-gray-700">{fmt(m.collections)}</td>
                      <td className="px-6 py-3 text-right">
                        <span className={`font-medium ${m.rate >= 95 ? 'text-emerald-600' : m.rate >= 80 ? 'text-amber-600' : 'text-red-600'}`}>
                          {m.rate.toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* AR Aging */}
        {arAging && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-medium text-gray-800 text-sm">Accounts Receivable Aging</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/50">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bucket</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Amount</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Patients</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {[
                    { label: 'Current', data: arAging.current, color: 'text-emerald-600' },
                    { label: '30 Days', data: arAging.thirty, color: 'text-blue-600' },
                    { label: '60 Days', data: arAging.sixty, color: 'text-amber-600' },
                    { label: '90 Days', data: arAging.ninety, color: 'text-orange-600' },
                    { label: '120+ Days', data: arAging.over120, color: 'text-red-600' },
                  ].map(row => (
                    <tr key={row.label} className="hover:bg-gray-50/50">
                      <td className="px-6 py-3 font-medium text-gray-700">{row.label}</td>
                      <td className={`px-6 py-3 text-right font-medium ${row.color}`}>{fmt(row.data.amount)}</td>
                      <td className="px-6 py-3 text-right text-gray-600">{row.data.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Provider Productivity */}
        {providers.length > 0 && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100">
              <h3 className="font-medium text-gray-800 text-sm">Provider Productivity</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/50">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Procedures</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Avg/Day</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total $</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {providers.map((p, i) => (
                    <tr key={i} className="hover:bg-gray-50/50">
                      <td className="px-6 py-3 font-medium text-gray-700">{p.provider_name}</td>
                      <td className="px-6 py-3 text-right text-gray-600">{p.total_procedures}</td>
                      <td className="px-6 py-3 text-right text-gray-600">{p.avg_per_day.toFixed(1)}</td>
                      <td className="px-6 py-3 text-right font-medium text-gray-700">{fmt(p.total_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        )}
          </>
  )
}

function MetricCard({ icon: Icon, label, value, color }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; value: string; color: string }) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
      <div className="w-8 h-8 bg-gray-50 rounded-lg flex items-center justify-center mb-3">
        <Icon size={16} className="text-gray-400" />
      </div>
      <p className={`text-2xl font-semibold ${color} tracking-tight`}>{value}</p>
      <p className="text-xs text-gray-500 mt-1">{label}</p>
    </div>
  )
}
