import { useState, useEffect, useCallback } from 'react'
import { Users, FileText, AlertTriangle, CheckCircle, XCircle, RefreshCw, Camera, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface ImagingAlert {
  id: string
  patient_id: string
  patient_name: string
  image_type: string
  due_date: string
  days_overdue: number
  treatment_phase: string
  rule_description: string
  status: 'pending' | 'dismissed' | 'completed'
  image_id: string | null
  created_at: string
}

interface AlertStats {
  total_overdue: number
  by_type: Record<string, number>
}

const TYPE_LABELS: Record<string, string> = {
  pano: 'Panoramic',
  ceph: 'Cephalometric',
  pa: 'Periapical',
  intraoral_photo: 'Intraoral Photo',
  cbct: 'CBCT',
  other: 'Other',
}

const TYPE_BADGES: Record<string, string> = {
  pano: 'bg-blue-100 text-blue-700',
  ceph: 'bg-violet-100 text-violet-700',
  pa: 'bg-emerald-100 text-emerald-700',
  intraoral_photo: 'bg-amber-100 text-amber-700',
  cbct: 'bg-rose-100 text-rose-700',
  other: 'bg-gray-100 text-gray-700',
}

export default function ImagingAlerts() {
  const [alerts, setAlerts] = useState<ImagingAlert[]>([])
  const [stats, setStats] = useState<AlertStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'pending' | 'dismissed' | 'all'>('pending')
  const loadAlerts = useCallback(async () => {
    setLoading(true)
    const statusParam = activeTab === 'all' ? undefined : activeTab
    const res = await api.getImagingAlerts({ status: statusParam })
    if (res.ok) {
      const data = await res.json()
      setAlerts(data.alerts || [])
      if (data.stats) setStats(data.stats)
    }
    setLoading(false)
  }, [activeTab])

  useEffect(() => { loadAlerts() }, [loadAlerts])

  async function handleGenerate() {
    setGenerating(true)
    const res = await api.generateImagingAlerts()
    if (res.ok) loadAlerts()
    setGenerating(false)
  }

  async function handleDismiss(id: string) {
    const res = await api.dismissAlert(id)
    if (res.ok) loadAlerts()
  }

  async function handleComplete(id: string) {
    const res = await api.completeAlert(id)
    if (res.ok) loadAlerts()
  }

  function getSeverityColor(days: number): string {
    if (days > 30) return 'text-red-600 bg-red-50'
    if (days > 7) return 'text-amber-600 bg-amber-50'
    return 'text-blue-600 bg-blue-50'
  }

  function getSeverityBorder(days: number): string {
    if (days > 30) return 'border-red-200'
    if (days > 7) return 'border-amber-200'
    return 'border-blue-200'
  }

  return (
    <>
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Imaging Alerts</h2>
            <p className="text-sm text-gray-500 mt-0.5">Overdue imaging notifications</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
          >
            {generating ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
            Generate Alerts
          </button>
        </div>

        {/* Stats */}
        {stats && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-6">
            <div className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
              <div className="w-8 h-8 bg-red-50 rounded-lg flex items-center justify-center mb-3">
                <AlertTriangle size={16} className="text-red-500" />
              </div>
              <p className="text-2xl font-semibold text-gray-900 tracking-tight">{stats.total_overdue}</p>
              <p className="text-xs text-gray-500 mt-1">Total Overdue</p>
            </div>
            {Object.entries(stats.by_type).slice(0, 3).map(([type, count]) => (
              <div key={type} className="bg-white rounded-2xl border border-gray-200/80 p-5 shadow-sm">
                <div className="w-8 h-8 bg-gray-50 rounded-lg flex items-center justify-center mb-3">
                  <Camera size={16} className="text-gray-400" />
                </div>
                <p className="text-2xl font-semibold text-gray-900 tracking-tight">{count}</p>
                <p className="text-xs text-gray-500 mt-1">{TYPE_LABELS[type] || type}</p>
              </div>
            ))}
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex gap-1 mb-6 bg-white rounded-xl border border-gray-200/80 p-1 shadow-sm w-fit">
          {(['pending', 'dismissed', 'all'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab ? 'bg-teal-600 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Alert List */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-medium text-gray-800">Alerts</h3>
            <span className="text-xs text-gray-400">{alerts.length} alert{alerts.length !== 1 ? 's' : ''}</span>
          </div>
          {loading ? (
            <div className="px-6 py-16 text-center"><p className="text-gray-400 text-sm">Loading alerts...</p></div>
          ) : alerts.length === 0 ? (
            <div className="px-6 py-16 text-center">
              <div className="w-16 h-16 bg-gray-50 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="text-gray-300" size={28} />
              </div>
              <p className="text-gray-500 font-medium">No alerts</p>
              <p className="text-gray-400 text-sm mt-1">{activeTab === 'pending' ? 'All patients are up to date on imaging' : 'No alerts in this category'}</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {alerts.map(alert => (
                <div key={alert.id} className={`px-4 sm:px-6 py-4 border-l-4 ${getSeverityBorder(alert.days_overdue)}`}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="font-medium text-gray-800 text-sm">{alert.patient_name}</p>
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${TYPE_BADGES[alert.image_type] || TYPE_BADGES.other}`}>
                          {TYPE_LABELS[alert.image_type] || alert.image_type}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-1">{alert.rule_description}</p>
                      <div className="flex items-center gap-3 text-xs text-gray-400">
                        <span>Due: {new Date(alert.due_date).toLocaleDateString()}</span>
                        <span className={`inline-flex px-2 py-0.5 rounded-full font-medium ${getSeverityColor(alert.days_overdue)}`}>
                          {alert.days_overdue} days overdue
                        </span>
                        <span>Phase: {alert.treatment_phase}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {alert.status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleDismiss(alert.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            <XCircle size={13} /> Dismiss
                          </button>
                          <button
                            onClick={() => handleComplete(alert.id)}
                            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-50 transition-colors"
                          >
                            <CheckCircle size={13} /> Mark Complete
                          </button>
                            </>
  )}
                      {alert.status === 'dismissed' && (
                        <span className="text-xs text-gray-400 italic">Dismissed</span>
                      )}
                      {alert.status === 'completed' && (
                        <span className="text-xs text-emerald-600 italic">Completed</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
          </>
  )
}
