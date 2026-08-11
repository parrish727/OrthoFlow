/**
 * Invisalign — Case management for clear aligner treatments.
 * Tracks cases from submission through completion, connected to doctor's Invisalign account.
 * Stages: ClinCheck Submitted → ClinCheck Approved → Aligners Ordered → In Treatment → Refinement → Complete
 */
import { useState, useEffect, useCallback } from 'react'
import { Plus, RefreshCw, Search, CheckCircle2, Clock, Package, AlertTriangle, Eye, Edit3, X, Smile } from 'lucide-react'
import { api } from '../lib/api'

// ── Types ────────────────────────────────────────────────────────────────────

interface InvisalignCase {
  id: string
  patient_id: string
  patient_name: string
  case_number: string
  status: string
  total_stages: number
  current_stage: number
  upper_aligners: number
  lower_aligners: number
  ipr_planned: boolean
  attachments_placed: boolean
  refinement_number: number
  clincheck_url: string | null
  notes: string | null
  started_at: string | null
  estimated_completion: string | null
  created_at: string
}

interface InvisalignSettings {
  provider_id: string
  provider_name: string
  practice_name: string
  tier: string
  cases_this_year: number
}

// ── Constants ────────────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  clincheck_submitted: { label: 'ClinCheck Submitted', color: 'bg-blue-100 text-blue-700', icon: Clock },
  clincheck_review: { label: 'ClinCheck Review', color: 'bg-indigo-100 text-indigo-700', icon: Eye },
  clincheck_approved: { label: 'ClinCheck Approved', color: 'bg-emerald-100 text-emerald-700', icon: CheckCircle2 },
  aligners_ordered: { label: 'Aligners Ordered', color: 'bg-amber-100 text-amber-700', icon: Package },
  aligners_received: { label: 'Aligners Received', color: 'bg-teal-100 text-teal-700', icon: Package },
  in_treatment: { label: 'In Treatment', color: 'bg-violet-100 text-violet-700', icon: Clock },
  refinement: { label: 'Refinement', color: 'bg-orange-100 text-orange-700', icon: RefreshCw },
  complete: { label: 'Complete', color: 'bg-green-100 text-green-800', icon: CheckCircle2 },
}

// ── Component ────────────────────────────────────────────────────────────────

export default function Invisalign() {
  const [cases, setCases] = useState<InvisalignCase[]>([])
  const [settings, setSettings] = useState<InvisalignSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [showNewCase, setShowNewCase] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  // New case form
  const [newCase, setNewCase] = useState({
    patient_name: '', patient_id: '', case_number: '',
    total_stages: 20, upper_aligners: 20, lower_aligners: 20,
    ipr_planned: false, notes: '',
  })
  const [patientResults, setPatientResults] = useState<{ id: string; first_name: string; last_name: string }[]>([])
  const [submitting, setSubmitting] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.request('/api/v1/invisalign/cases')
      if (res.ok) {
        const data = await res.json()
        setCases(data.cases || [])
      }
    } catch {}
    try {
      const res = await api.request('/api/v1/invisalign/settings')
      if (res.ok) setSettings(await res.json())
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { fetchData() }, [fetchData])

  const filteredCases = cases.filter(c => {
    if (searchQuery && !(c.patient_name || '').toLowerCase().includes(searchQuery.toLowerCase()) && !c.case_number.includes(searchQuery)) return false
    if (statusFilter && c.status !== statusFilter) return false
    return true
  })

  async function handleCreateCase() {
    if (!newCase.patient_id || !newCase.case_number) return
    setSubmitting(true)
    try {
      await api.request('/api/v1/invisalign/cases', {
        method: 'POST',
        body: JSON.stringify(newCase),
      })
      setShowNewCase(false)
      setNewCase({ patient_name: '', patient_id: '', case_number: '', total_stages: 20, upper_aligners: 20, lower_aligners: 20, ipr_planned: false, notes: '' })
      fetchData()
    } catch {}
    setSubmitting(false)
  }

  async function handleUpdateStatus(caseId: string, newStatus: string) {
    await api.request(`/api/v1/invisalign/cases/${caseId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    })
    fetchData()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Invisalign</h1>
          <p className="text-sm text-gray-500 mt-1">Clear aligner case management</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setShowSettings(true)} className="px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors">
            Provider Settings
          </button>
          <button onClick={() => setShowNewCase(true)} className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors">
            <Plus className="h-4 w-4" /> New Case
          </button>
        </div>
      </div>

      {/* Provider Stats */}
      {settings && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Provider</p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{settings.provider_name}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Tier</p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{settings.tier}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Cases This Year</p>
            <p className="text-sm font-semibold text-gray-900 mt-1">{settings.cases_this_year}</p>
          </div>
          <div className="bg-white rounded-xl border border-gray-200 p-4">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Active Cases</p>
            <p className="text-sm font-semibold text-teal-600 mt-1">{cases.filter(c => c.status !== 'complete').length}</p>
          </div>
        </div>
      )}

      {/* Search & Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by patient or case number..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-teal-500/20"
          />
        </div>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white">
          <option value="">All Statuses</option>
          {Object.entries(STATUS_CONFIG).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
      </div>

      {/* Cases Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading cases...</div>
        ) : filteredCases.length === 0 ? (
          <div className="p-12 text-center">
            <Package className="h-12 w-12 mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500 font-medium">No Invisalign cases</p>
            <p className="text-gray-400 text-sm mt-1">Create a case to start tracking a patient's aligner treatment</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Patient</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Case #</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Progress</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">IPR</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Attachments</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {filteredCases.map(c => {
                  const config = STATUS_CONFIG[c.status] || STATUS_CONFIG.clincheck_submitted
                  const Icon = config.icon
                  const progress = c.total_stages > 0 ? Math.round((c.current_stage / c.total_stages) * 100) : 0
                  return (
                    <tr key={c.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-medium text-gray-900">{c.patient_name}</td>
                      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{c.case_number}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
                          <Icon className="h-3 w-3" /> {config.label}
                        </span>
                        {c.refinement_number > 0 && <span className="ml-1 text-xs text-orange-600">R{c.refinement_number}</span>}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                            <div className="h-full bg-teal-500 rounded-full" style={{ width: `${progress}%` }} />
                          </div>
                          <span className="text-xs text-gray-500">{c.current_stage}/{c.total_stages}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        {c.ipr_planned ? <span className="text-xs text-blue-600 font-medium">Planned</span> : <span className="text-xs text-gray-400">None</span>}
                      </td>
                      <td className="px-4 py-3">
                        {c.attachments_placed ? <CheckCircle2 className="h-4 w-4 text-green-500" /> : <span className="text-xs text-gray-400">Pending</span>}
                      </td>
                      <td className="px-4 py-3">
                        <select
                          value=""
                          onChange={e => { if (e.target.value) handleUpdateStatus(c.id, e.target.value) }}
                          className="text-xs px-2 py-1 border border-gray-200 rounded bg-white text-gray-600"
                        >
                          <option value="">Advance →</option>
                          {Object.entries(STATUS_CONFIG).filter(([k]) => k !== c.status).map(([k, v]) => (
                            <option key={k} value={k}>{v.label}</option>
                          ))}
                        </select>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Case Modal */}
      {showNewCase && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowNewCase(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">New Invisalign Case</h3>
              <button onClick={() => setShowNewCase(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Patient</label>
                <input
                  type="text"
                  placeholder="Search patient..."
                  value={newCase.patient_name}
                  onChange={async e => {
                    setNewCase(f => ({ ...f, patient_name: e.target.value }))
                    if (e.target.value.length >= 2) {
                      const res = await api.getPatients({ search: e.target.value })
                      if (res.ok) setPatientResults((await res.json()).patients || [])
                    } else setPatientResults([])
                  }}
                  className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg"
                />
                {patientResults.length > 0 && (
                  <div className="mt-1 border border-gray-200 rounded-lg max-h-32 overflow-y-auto">
                    {patientResults.map(p => (
                      <button key={p.id} onClick={() => { setNewCase(f => ({ ...f, patient_id: p.id, patient_name: `${p.first_name} ${p.last_name}` })); setPatientResults([]) }} className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50">
                        {p.first_name} {p.last_name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Invisalign Case Number</label>
                <input type="text" value={newCase.case_number} onChange={e => setNewCase(f => ({ ...f, case_number: e.target.value }))} placeholder="e.g., INV-2026-00142" className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg" />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Total Stages</label>
                  <input type="number" value={newCase.total_stages} onChange={e => setNewCase(f => ({ ...f, total_stages: parseInt(e.target.value) || 0 }))} className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Upper #</label>
                  <input type="number" value={newCase.upper_aligners} onChange={e => setNewCase(f => ({ ...f, upper_aligners: parseInt(e.target.value) || 0 }))} className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Lower #</label>
                  <input type="number" value={newCase.lower_aligners} onChange={e => setNewCase(f => ({ ...f, lower_aligners: parseInt(e.target.value) || 0 }))} className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg" />
                </div>
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-700">
                <input type="checkbox" checked={newCase.ipr_planned} onChange={e => setNewCase(f => ({ ...f, ipr_planned: e.target.checked }))} className="rounded border-gray-300" />
                IPR Planned
              </label>
              <div>
                <label className="text-xs font-medium text-gray-600 uppercase tracking-wide">Notes</label>
                <textarea value={newCase.notes} onChange={e => setNewCase(f => ({ ...f, notes: e.target.value }))} placeholder="ClinCheck notes, treatment goals..." rows={3} className="w-full mt-1 px-3 py-2 text-sm border border-gray-200 rounded-lg resize-none" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button onClick={() => setShowNewCase(false)} className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg">Cancel</button>
                <button onClick={handleCreateCase} disabled={!newCase.patient_id || !newCase.case_number || submitting} className="px-4 py-2 text-sm bg-teal-600 hover:bg-teal-700 text-white font-medium rounded-lg disabled:opacity-50">
                  {submitting ? 'Creating...' : 'Create Case'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Provider Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setShowSettings(false)} />
          <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg p-6 mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Invisalign Provider Account</h3>
              <button onClick={() => setShowSettings(false)} className="p-1 hover:bg-gray-100 rounded-lg"><X className="h-5 w-5 text-gray-400" /></button>
            </div>
            <div className="space-y-5">
              {/* Connection Status */}
              {settings && settings.provider_id ? (
                <>
                  <div className="flex items-center gap-3 px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                    <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-sm font-medium text-emerald-800">Connected to Invisalign Doctor Site</span>
                  </div>

                  <div className="space-y-3 bg-gray-50 rounded-xl p-4">
                    <div className="flex justify-between text-sm"><span className="text-gray-500">Provider ID</span><span className="font-mono text-gray-900">{settings.provider_id}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-gray-500">Provider</span><span className="text-gray-900">{settings.provider_name}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-gray-500">Practice</span><span className="text-gray-900">{settings.practice_name}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-gray-500">Tier</span><span className="font-semibold text-teal-600">{settings.tier}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-gray-500">Cases This Year</span><span className="text-gray-900">{settings.cases_this_year}</span></div>
                  </div>

                  {/* Quick Actions — replaces need to leave OrthoFlow */}
                  <div>
                    <p className="text-xs font-semibold text-gray-600 uppercase tracking-wider mb-3">Quick Actions</p>
                    <div className="grid grid-cols-2 gap-2">
                      <a href="https://myaccount-us.aligntech.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-teal-300 hover:text-teal-700 transition-colors">
                        <Eye className="h-4 w-4" /> View ClinChecks
                      </a>
                      <a href="https://myaccount-us.aligntech.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-teal-300 hover:text-teal-700 transition-colors">
                        <Plus className="h-4 w-4" /> Submit Case
                      </a>
                      <a href="https://myaccount-us.aligntech.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-teal-300 hover:text-teal-700 transition-colors">
                        <Package className="h-4 w-4" /> Track Orders
                      </a>
                      <a href="https://myaccount-us.aligntech.com" target="_blank" rel="noopener noreferrer" className="flex items-center gap-2 px-3 py-2.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:border-teal-300 hover:text-teal-700 transition-colors">
                        <RefreshCw className="h-4 w-4" /> Resources
                      </a>
                    </div>
                  </div>

                  <p className="text-xs text-gray-400 text-center">Your Invisalign account is synced. Cases created here automatically sync with the Doctor Site.</p>
                </>
              ) : (
                <>
                  {/* Not Connected — Show connect flow */}
                  <div className="text-center py-6">
                    <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <Smile className="h-8 w-8 text-gray-400" />
                    </div>
                    <h4 className="font-semibold text-gray-900 mb-1">Connect Your Invisalign Account</h4>
                    <p className="text-sm text-gray-500 mb-4">Link your Invisalign Doctor Site credentials to manage cases, view ClinChecks, and track orders — all from within OrthoFlow.</p>
                    <a
                      href="https://myaccount-us.aligntech.com"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white text-sm font-medium rounded-lg transition-colors"
                    >
                      Connect Invisalign Account
                    </a>
                  </div>
                  <div className="border-t border-gray-100 pt-4">
                    <p className="text-xs text-gray-400 text-center">Once connected, you can submit cases, approve ClinChecks, and track aligner deliveries without leaving OrthoFlow.</p>
                  </div>
                </>
              )}

              <button onClick={() => setShowSettings(false)} className="w-full py-2.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg mt-2">Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
