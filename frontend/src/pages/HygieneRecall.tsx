/**
 * HygieneRecall — practice-wide recall management dashboard.
 * Shows due/overdue patients, stats, and quick-complete actions.
 * Fetches from /api/v1/recall/due-list, /api/v1/recall/overdue, /api/v1/recall/stats
 */
import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Calendar, Clock, AlertTriangle, CheckCircle, Users, RefreshCw, Phone } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
function authFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('token')
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
}

interface RecallPatient {
  patient_id: string
  patient_name: string
  recall_type: string
  next_due_date: string
  last_visit_date: string | null
  interval_months: number
  days_overdue: number
  phone: string | null
}

interface RecallStats {
  active_recalls: number
  due_this_month: number
  overdue: number
  compliance_rate: number
}

const RECALL_TYPE_LABELS: Record<string, { label: string; color: string }> = {
  prophy: { label: 'Prophy', color: 'bg-blue-100 text-blue-700' },
  perio_maintenance: { label: 'Perio Maint', color: 'bg-orange-100 text-orange-700' },
  fluoride: { label: 'Fluoride', color: 'bg-purple-100 text-purple-700' },
  sealant_check: { label: 'Sealant Check', color: 'bg-green-100 text-green-700' },
}

export default function HygieneRecall() {
  const [dueList, setDueList] = useState<RecallPatient[]>([])
  const [overdueList, setOverdueList] = useState<RecallPatient[]>([])
  const [stats, setStats] = useState<RecallStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<'due' | 'overdue'>('due')
  const [completing, setCompleting] = useState<string | null>(null)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [dueRes, overdueRes, statsRes] = await Promise.all([
        authFetch('/api/v1/recall/due-list'),
        authFetch('/api/v1/recall/overdue'),
        authFetch('/api/v1/recall/stats'),
      ])
      if (dueRes.ok) setDueList(await dueRes.json())
      if (overdueRes.ok) setOverdueList(await overdueRes.json())
      if (statsRes.ok) setStats(await statsRes.json())
    } catch { /* silent */ }
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const handleComplete = async (patientId: string) => {
    setCompleting(patientId)
    try {
      const res = await authFetch(`/api/v1/recall/patients/${patientId}/complete`, { method: 'POST' })
      if (res.ok) fetchData()
    } catch { /* silent */ }
    setCompleting(null)
  }

  const activeList = tab === 'due' ? dueList : overdueList

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Hygiene Recall</h1>
          <p className="text-xs text-gray-500 mt-0.5">Track and manage patient recall schedules</p>
        </div>
        <button
          onClick={fetchData}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors"
        >
          <RefreshCw size={12} /> Refresh
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Users size={14} className="text-teal-600" />
              <span className="text-[10px] uppercase tracking-wide text-gray-500">Active Recalls</span>
            </div>
            <div className="text-2xl font-semibold text-gray-900">{stats.active_recalls}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <Calendar size={14} className="text-blue-600" />
              <span className="text-[10px] uppercase tracking-wide text-gray-500">Due This Month</span>
            </div>
            <div className="text-2xl font-semibold text-blue-700">{stats.due_this_month}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <AlertTriangle size={14} className="text-red-600" />
              <span className="text-[10px] uppercase tracking-wide text-gray-500">Overdue</span>
            </div>
            <div className="text-2xl font-semibold text-red-700">{stats.overdue}</div>
          </div>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle size={14} className="text-green-600" />
              <span className="text-[10px] uppercase tracking-wide text-gray-500">Compliance Rate</span>
            </div>
            <div className="text-2xl font-semibold text-green-700">{stats.compliance_rate}%</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex border-b border-gray-200">
          <button
            onClick={() => setTab('due')}
            className={`flex-1 px-4 py-2.5 text-xs font-medium transition-colors ${
              tab === 'due' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Calendar size={12} className="inline mr-1" /> Due ({dueList.length})
          </button>
          <button
            onClick={() => setTab('overdue')}
            className={`flex-1 px-4 py-2.5 text-xs font-medium transition-colors ${
              tab === 'overdue' ? 'bg-red-50 text-red-700 border-b-2 border-red-600' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <AlertTriangle size={12} className="inline mr-1" /> Overdue ({overdueList.length})
          </button>
        </div>

        {/* Patient List */}
        <div className="divide-y divide-gray-100">
          {loading ? (
            <div className="p-8 text-center text-sm text-gray-400">Loading recall data...</div>
          ) : activeList.length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle size={20} className="mx-auto text-green-300 mb-2" />
              <p className="text-sm text-gray-400">
                {tab === 'due' ? 'No recalls due at this time' : 'No overdue recalls — great job!'}
              </p>
            </div>
          ) : (
            activeList.map(patient => {
              const typeConfig = RECALL_TYPE_LABELS[patient.recall_type] || { label: patient.recall_type, color: 'bg-gray-100 text-gray-700' }
              return (
                <div key={`${patient.patient_id}-${patient.recall_type}`} className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors">
                  <div className="flex-1 min-w-0">
                    <Link
                      to={`/patients/${patient.patient_id}`}
                      className="text-sm font-medium text-gray-900 hover:text-teal-700 transition-colors"
                    >
                      {patient.patient_name}
                    </Link>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className={`inline-block px-1.5 py-0.5 text-[9px] font-medium rounded ${typeConfig.color}`}>
                        {typeConfig.label}
                      </span>
                      <span className="text-[10px] text-gray-400">
                        Every {patient.interval_months}mo
                      </span>
                      {patient.last_visit_date && (
                        <span className="text-[10px] text-gray-400">
                          Last: {new Date(patient.last_visit_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="text-right">
                    <div className={`text-xs font-medium ${patient.days_overdue > 0 ? 'text-red-600' : 'text-gray-700'}`}>
                      {patient.days_overdue > 0
                        ? `${patient.days_overdue}d overdue`
                        : `Due ${new Date(patient.next_due_date).toLocaleDateString()}`
                      }
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {patient.phone && (
                      <a
                        href={`tel:${patient.phone}`}
                        className="p-1.5 rounded-lg bg-gray-100 text-gray-500 hover:bg-blue-100 hover:text-blue-600 transition-colors"
                        title="Call patient"
                      >
                        <Phone size={12} />
                      </a>
                    )}
                    <button
                      onClick={() => handleComplete(patient.patient_id)}
                      disabled={completing === patient.patient_id}
                      className="px-2.5 py-1 text-[10px] font-medium bg-green-50 text-green-700 rounded-lg hover:bg-green-100 disabled:opacity-50 transition-colors"
                      title="Mark recall completed"
                    >
                      {completing === patient.patient_id ? '...' : '✓ Complete'}
                    </button>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
