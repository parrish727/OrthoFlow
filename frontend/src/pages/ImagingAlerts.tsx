import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Bell, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, AlertTriangle, CheckCircle,
  XCircle, RefreshCw, MessageSquare, MessagesSquare, Camera, Loader2,
  Sparkles, Wrench,
} from 'lucide-react'
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
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)

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
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {practiceLogo ? (
              <img src={practiceLogo} alt="" className="w-8 h-8 rounded-lg object-contain" />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Bell size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Imaging Alerts</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative" ref={menuRef}>
              <button onClick={() => setMenuOpen(!menuOpen)} className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors">
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
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Imaging Alerts</h2>
            <p className="text-sm text-gray-500 mt-0.5">Overdue imaging notifications</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
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
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${activeTab === tab ? 'bg-blue-500 text-white shadow-sm' : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'}`}
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
      </main>
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
