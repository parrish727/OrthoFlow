import { useState, useEffect, useCallback } from 'react'
import { Download, DollarSign, TrendingUp, Percent, Clock, PieChart } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../lib/api'

interface ProductionData {
  period: string
  total_production: number
  total_procedures: number
  by_provider: { provider_id: string; provider_label: string; total_charges: number; procedure_count: number }[]
  by_cdt_category: { cdt_category: string; total_charges: number; procedure_count: number }[]
}

interface CollectionsData {
  period: string
  total_production: number
  total_collections: number
  overall_collection_rate: number
  monthly: { month: string; production: number; collections: number; collection_rate: number }[]
}

interface ArAgingData {
  total_outstanding: number
  buckets: { bucket: string; total_amount: number; patient_count: number }[]
}

interface ProviderProductivityData {
  providers: { provider_id: string; provider_label: string; total_procedures: number; total_production: number; avg_per_day: number }[]
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
  const [collections, setCollections] = useState<CollectionsData | null>(null)
  const [arAging, setArAging] = useState<ArAgingData | null>(null)
  const [providerProductivity, setProviderProductivity] = useState<ProviderProductivityData | null>(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const loadReports = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params: Record<string, string> = { start_date: startDate, end_date: endDate }
      if (provider) params.provider = provider

      const [prodRes, collectRes, arRes, provRes] = await Promise.all([
        api.reportsProduction(params),
        api.reportsCollections(params),
        api.reportsArAging(params),
        api.reportsProviderProductivity(params),
      ])

      if (prodRes.ok) {
        setProduction(await prodRes.json())
      } else {
        setProduction(null)
      }

      if (collectRes.ok) {
        setCollections(await collectRes.json())
      } else {
        setCollections(null)
      }

      if (arRes.ok) {
        setArAging(await arRes.json())
      } else {
        setArAging(null)
      }

      if (provRes.ok) {
        setProviderProductivity(await provRes.json())
      } else {
        setProviderProductivity(null)
      }
    } catch {
      setError('Failed to load reports — connection error')
    }
    setLoading(false)
  }, [startDate, endDate, provider])

  useEffect(() => { loadReports() }, [loadReports])

  function exportCSV() {
    if (!collections) return
    const monthly = collections.monthly || []
    if (monthly.length === 0) return
    const headers = ['Month', 'Production', 'Collections', 'Rate %']
    const rows = monthly.map(m => [
      m.month || '',
      (m.production || 0).toFixed(2),
      (m.collections || 0).toFixed(2),
      (m.collection_rate || 0).toFixed(1),
    ])
    const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `orthoflow-report-${startDate}-${endDate}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function fmt(n: number | undefined | null): string {
    return '$' + (n || 0).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  }

  const providerList = providerProductivity?.providers || []
  const monthlyData = collections?.monthly || []

  // Consultant reports state
  const [reportTab, setReportTab] = useState<'financial' | 'consultant'>('financial')
  const [consultantData, setConsultantData] = useState<Record<string, unknown> | null>(null)
  const [consultantLoading, setConsultantLoading] = useState(false)
  const [selectedReport, setSelectedReport] = useState('')

  async function loadConsultantReport(report: string) {
    setConsultantLoading(true)
    setSelectedReport(report)
    try {
      const token = localStorage.getItem('token')
      const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
      const res = await fetch(`${baseUrl}/api/v1/reports/consultant/${report}`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) setConsultantData(await res.json())
    } catch {}
    setConsultantLoading(false)
  }

  function handleExportEmail() {
    const subject = encodeURIComponent(`OrthoFlow Practice Report — ${selectedReport.replace(/-/g, ' ')}`)
    const body = encodeURIComponent(`Practice Optimization Report\n\n${JSON.stringify(consultantData, null, 2)}`)
    window.open(`mailto:?subject=${subject}&body=${body}`)
  }

  return (
    <>
      {/* Tab Switcher */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        <button onClick={() => setReportTab('financial')} className={`px-4 py-2 text-xs font-medium rounded-md transition-colors ${reportTab === 'financial' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Financial Reports</button>
        <button onClick={() => setReportTab('consultant')} className={`px-4 py-2 text-xs font-medium rounded-md transition-colors ${reportTab === 'consultant' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'}`}>Consultant Reports</button>
      </div>

      {reportTab === 'consultant' ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Practice Optimization Reports</h2>
              <p className="text-xs text-gray-500 mt-0.5">Pull reports to help optimize practice performance</p>
            </div>
            {consultantData && (
              <button onClick={handleExportEmail} className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors">
                <Download size={14} /> Export via Email
              </button>
            )}
          </div>

          {/* Report Selection */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {[
              { id: 'summary', label: 'Executive Summary', desc: 'Overall practice health' },
              { id: 'treatment-starts', label: 'Treatment Starts', desc: 'Active vs pending conversion' },
              { id: 'missing-appointments', label: 'Missing Appointments', desc: 'No-shows & cancellations' },
              { id: 'active-no-next-appointment', label: 'No Next Appointment', desc: 'Active patients without future appt' },
              { id: 'observation-report', label: 'Observation Patients', desc: 'Pipeline for conversion' },
              { id: 'pending-no-start', label: 'Pending (No Start)', desc: 'Consulted but not started' },
              { id: 'overdue-payments', label: 'Overdue Payments', desc: 'Past due balances' },
            ].map(r => (
              <button key={r.id} onClick={() => loadConsultantReport(r.id)} className={`text-left p-3 border rounded-xl transition-colors ${selectedReport === r.id ? 'border-teal-500 bg-teal-50' : 'border-gray-200 hover:border-teal-300 hover:bg-teal-50/30'}`}>
                <p className="text-sm font-medium text-gray-900">{r.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{r.desc}</p>
              </button>
            ))}
          </div>

          {/* Report Results */}
          {consultantLoading ? (
            <div className="text-center py-12 text-gray-400"><p className="text-sm">Loading report...</p></div>
          ) : consultantData ? (
            <div className="bg-white rounded-2xl border border-gray-200 p-5">
              <h3 className="text-sm font-semibold text-gray-900 mb-4 capitalize">{selectedReport.replace(/-/g, ' ')}</h3>
              {/* Render based on report type */}
              {selectedReport === 'summary' && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  {Object.entries(consultantData as Record<string, number | string>).filter(([k]) => k !== 'period').map(([key, val]) => (
                    <div key={key} className="text-center p-3 bg-gray-50 rounded-xl">
                      <p className="text-lg font-bold text-gray-900">{typeof val === 'number' && key.includes('rate') ? `${val}%` : val}</p>
                      <p className="text-xs text-gray-500 mt-0.5 capitalize">{key.replace(/_/g, ' ')}</p>
                    </div>
                  ))}
                </div>
              )}
              {(consultantData as { patients?: unknown[] }).patients && (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left px-3 py-2 font-medium text-gray-600">Patient</th>
                        <th className="text-left px-3 py-2 font-medium text-gray-600">Phone</th>
                        <th className="text-left px-3 py-2 font-medium text-gray-600">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {((consultantData as { patients: { patient_name: string; phone?: string; treatment_phase?: string; balance?: number; days_since_consult?: number; missed_date?: string }[] }).patients || []).map((p, i) => (
                        <tr key={i} className="hover:bg-gray-50">
                          <td className="px-3 py-2 font-medium text-gray-900">{p.patient_name}</td>
                          <td className="px-3 py-2 text-gray-600">{p.phone || '—'}</td>
                          <td className="px-3 py-2 text-gray-500 text-xs">
                            {p.treatment_phase && <span className="capitalize">{p.treatment_phase}</span>}
                            {p.balance && <span className="text-red-600 font-medium">${p.balance.toLocaleString()}</span>}
                            {p.days_since_consult && <span>{p.days_since_consult} days since consult</span>}
                            {p.missed_date && <span>Missed: {p.missed_date}</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  <p className="text-xs text-gray-400 mt-3 text-right">
                    {((consultantData as { patients?: unknown[] }).patients || []).length} patient(s) • {(consultantData as { total_overdue_amount?: number }).total_overdue_amount ? `Total: $${(consultantData as { total_overdue_amount: number }).total_overdue_amount.toLocaleString()}` : ''}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-400">
              <TrendingUp size={32} className="mx-auto mb-3 opacity-50" />
              <p className="text-sm">Select a report to view practice data</p>
            </div>
          )}
        </div>
      ) : (
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
            {providerList.map(p => (
              <option key={p.provider_id} value={p.provider_id}>{p.provider_label || ''}</option>
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
      {(production || collections || arAging) && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
          <MetricCard
            icon={DollarSign}
            label="Total Production"
            value={fmt(production?.total_production)}
            color="text-blue-600"
          />
          <MetricCard
            icon={TrendingUp}
            label="Total Collections"
            value={fmt(collections?.total_collections)}
            color="text-emerald-600"
          />
          <MetricCard
            icon={Percent}
            label="Collection Rate"
            value={`${(collections?.overall_collection_rate || 0).toFixed(1)}%`}
            color="text-violet-600"
          />
          <MetricCard
            icon={Clock}
            label="AR Outstanding"
            value={fmt(arAging?.total_outstanding)}
            color="text-amber-600"
          />
        </div>
      )}

      {/* Production by Provider */}
      {production && (production.by_provider || []).length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-medium text-gray-800 text-sm">Production by Provider</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Provider</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Charges</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Procedures</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(production.by_provider || []).map((p, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-gray-700">{p.provider_label || ''}</td>
                    <td className="px-6 py-3 text-right text-gray-700">{fmt(p.total_charges)}</td>
                    <td className="px-6 py-3 text-right text-gray-600">{(p.procedure_count || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Production by CDT Category */}
      {production && (production.by_cdt_category || []).length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-medium text-gray-800 text-sm">Production by CDT Category</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Category</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Charges</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Procedures</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {(production.by_cdt_category || []).map((c, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-gray-700">{c.cdt_category || ''}</td>
                    <td className="px-6 py-3 text-right text-gray-700">{fmt(c.total_charges)}</td>
                    <td className="px-6 py-3 text-right text-gray-600">{(c.procedure_count || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Collections Chart */}
      {monthlyData.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 mb-6">
          <h3 className="font-medium text-gray-800 text-sm mb-4">Production vs Collections</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${((v || 0) / 1000).toFixed(0)}k`} />
                <Tooltip formatter={(value: number) => ['$' + (value || 0).toLocaleString()]} />
                <Legend />
                <Bar dataKey="production" fill="#3b82f6" name="Production" radius={[4, 4, 0, 0]} />
                <Bar dataKey="collections" fill="#10b981" name="Collections" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Monthly Breakdown Table */}
      {monthlyData.length > 0 && (
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
                {monthlyData.map((m, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-gray-700">{m.month || ''}</td>
                    <td className="px-6 py-3 text-right text-gray-700">{fmt(m.production)}</td>
                    <td className="px-6 py-3 text-right text-gray-700">{fmt(m.collections)}</td>
                    <td className="px-6 py-3 text-right">
                      <span className={`font-medium ${(m.collection_rate || 0) >= 95 ? 'text-emerald-600' : (m.collection_rate || 0) >= 80 ? 'text-amber-600' : 'text-red-600'}`}>
                        {(m.collection_rate || 0).toFixed(1)}%
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
      {arAging && (arAging.buckets || []).length > 0 && (
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
                {(arAging.buckets || []).map((b, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-gray-700">{b.bucket || ''}</td>
                    <td className="px-6 py-3 text-right font-medium text-gray-700">{fmt(b.total_amount)}</td>
                    <td className="px-6 py-3 text-right text-gray-600">{(b.patient_count || 0).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Provider Productivity */}
      {providerList.length > 0 && (
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
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total Production</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {providerList.map((p, i) => (
                  <tr key={i} className="hover:bg-gray-50/50">
                    <td className="px-6 py-3 font-medium text-gray-700">{p.provider_label || ''}</td>
                    <td className="px-6 py-3 text-right text-gray-600">{(p.total_procedures || 0).toLocaleString()}</td>
                    <td className="px-6 py-3 text-right text-gray-600">{(p.avg_per_day || 0).toFixed(1)}</td>
                    <td className="px-6 py-3 text-right font-medium text-gray-700">{fmt(p.total_production)}</td>
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

      {error && (
        <div className="p-3 rounded-xl bg-red-50 text-red-700 text-sm border border-red-100">{error}</div>
      )}

      {!loading && !error && !production && !collections && !arAging && providerList.length === 0 && (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-16 text-center">
          <PieChart size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No report data available for the selected date range</p>
        </div>
      )}
    </>
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
