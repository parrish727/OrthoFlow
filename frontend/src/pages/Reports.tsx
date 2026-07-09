import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart3, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, MessageSquare, MessagesSquare,
  Camera, Bell, Sparkles, Wrench, Download, DollarSign, TrendingUp,
  Percent, Clock, Filter, PieChart, ArrowUpRight, UserCog,
} from 'lucide-react'
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
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    api.getPractice().then(async res => {
      if (res.ok) { const data = await res.json(); setPracticeName(data.name || 'OrthoFlow'); setPracticeLogo(data.logo_url || '') }
    })
  }, [])

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
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {practiceLogo ? (
              <img src={practiceLogo} alt="" className="w-8 h-8 rounded-lg object-contain" />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <FileText size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Financial Reports</p>
            </div>
          </div>

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
                  <DropdownItem icon={CalendarDays} label="Schedule" description="Daily appointment board" onClick={() => { setMenuOpen(false); navigate('/schedule') }} />
                  <DropdownItem icon={Users} label="Patients" description="Patient records" onClick={() => { setMenuOpen(false); navigate('/patients') }} />
                  <DropdownItem icon={BookOpen} label="Ledger" description="Patient financials" onClick={() => { setMenuOpen(false); navigate('/ledger') }} />
                  <DropdownItem icon={Shield} label="Insurance" description="Plans & eligibility" onClick={() => { setMenuOpen(false); navigate('/insurance') }} />
                  <DropdownItem icon={FileText} label="Claims" description="Claims management" onClick={() => { setMenuOpen(false); navigate('/claims') }} />
                  <DropdownItem icon={Banknote} label="Payments" description="Payment posting" onClick={() => { setMenuOpen(false); navigate('/payments') }} />
                  <DropdownItem icon={MessageSquare} label="Communications" description="Templates & send" onClick={() => { setMenuOpen(false); navigate('/communications') }} />
                  <DropdownItem icon={MessagesSquare} label="Messages" description="Delivery log" onClick={() => { setMenuOpen(false); navigate('/messages') }} />
                  <DropdownItem icon={Camera} label="Imaging" description="Patient images" onClick={() => { setMenuOpen(false); navigate('/imaging') }} />
                  <DropdownItem icon={Bell} label="Imaging Alerts" description="Overdue imaging" onClick={() => { setMenuOpen(false); navigate('/imaging/alerts') }} />
                  <DropdownItem icon={Sparkles} label="AI Insights" description="Intelligence dashboard" onClick={() => { setMenuOpen(false); navigate('/ai-insights') }} />
                  <DropdownItem icon={Wrench} label="AI Tools" description="Referrals & summaries" onClick={() => { setMenuOpen(false); navigate('/ai-tools') }} />
                  <DropdownItem icon={BarChart3} label="Reports" description="Financial reports" onClick={() => { setMenuOpen(false); navigate('/reports') }} />
                  <DropdownItem icon={ArrowUpRight} label="Migration" description="Patient data import" onClick={() => { setMenuOpen(false); navigate('/migration') }} />
                  <DropdownItem icon={UserCog} label="Portal Admin" description="Patient portal mgmt" onClick={() => { setMenuOpen(false); navigate('/portal-admin') }} />
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
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
      </main>
    </div>
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

function DropdownItem({ icon: Icon, label, description, onClick }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; description: string; onClick: () => void }) {
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
