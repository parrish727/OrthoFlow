import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Users, Plus, Clock, X, Loader2, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  middle_name: string | null
  last_name: string
  date_of_birth: string | null
  gender: string | null
  email: string | null
  phone: string | null
  address: string | null
  responsible_party: string | null
  status: string | null
  treatment_phase: string | null
  referring_doctor: string | null
  created_at: string | null
  visit_status: string | null
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  active: { label: 'Active', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  inactive: { label: 'Inactive', color: 'bg-gray-50 text-gray-600 border-gray-200' },
  archived: { label: 'Archived', color: 'bg-red-50 text-red-600 border-red-200' },
}

const VISIT_STATUS_BADGES: Record<string, { label: string; color: string }> = {
  lobby: { label: 'In Lobby', color: 'bg-amber-100 text-amber-800' },
  seated: { label: 'Seated', color: 'bg-blue-100 text-blue-800' },
  checked_out: { label: 'Checked Out', color: 'bg-purple-100 text-purple-800' },
  dismissed: { label: 'Dismissed', color: 'bg-gray-100 text-gray-600' },
}

const PHASE_LABELS: Record<string, string> = {
  consultation: 'Consultation',
  pending: 'Pending',
  records: 'Records',
  treatment_planning: 'Treatment Planning',
  active_treatment: 'Active Treatment',
  retention: 'Retention',
  completed: 'Completed',
  // Observation phases
  observation_1: 'Observation 1',
  observation_2: 'Observation 2',
  observation_3: 'Observation 3',
  observation_4: 'Observation 4',
  // GP
  new_patient: 'New Patient',
  active_gp: 'Active GP',
  hygiene_recall: 'Hygiene/Recall',
  restorative: 'Restorative',
  // Ortho
  bonding: 'Bonding',
  active: 'Active Ortho',
  finishing: 'Finishing',
  complete: 'Complete',
  // Cosmetic
  cosmetic_consult: 'Cosmetic Consult',
  cosmetic_active: 'Cosmetic Treatment',
  // Perio
  perio_active: 'Perio Treatment',
  perio_maintenance: 'Perio Maintenance',
}

const TREATMENT_PHASE_OPTIONS = [
  { value: 'consultation', label: 'Consultation' },
  { value: 'pending', label: 'Pending' },
  { value: 'observation_1', label: 'Observation 1' },
  { value: 'observation_2', label: 'Observation 2' },
  { value: 'observation_3', label: 'Observation 3' },
  { value: 'observation_4', label: 'Observation 4' },
  { value: 'records', label: 'Records' },
  { value: 'bonding', label: 'Bonding' },
  { value: 'active', label: 'Active Ortho' },
  { value: 'finishing', label: 'Finishing' },
  { value: 'retention', label: 'Retention' },
  { value: 'complete', label: 'Complete' },
  { value: 'new_patient', label: 'New Patient' },
  { value: 'active_gp', label: 'Active GP' },
  { value: 'hygiene_recall', label: 'Hygiene/Recall' },
  { value: 'restorative', label: 'Restorative' },
]

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedPatient, setExpandedPatient] = useState<string | null>(null)
  const [phaseDropdownPatient, setPhaseDropdownPatient] = useState<string | null>(null)
  const navigate = useNavigate()

  // Create Patient Modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState('')
  const [newPatient, setNewPatient] = useState({
    first_name: '',
    middle_name: '',
    last_name: '',
    date_of_birth: '',
    gender: '',
    email: '',
    phone: '',
    responsible_party: '',
    treatment_phase: '',
    referring_doctor: '',
    sms_consent: true,
    email_consent: true,
  })
const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const loadPatients = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await api.getPatients({ search, status: statusFilter, page })
      if (res.ok) {
        const data = await res.json()
        setPatients(data.patients)
        setTotal(data.total)
      } else {
        setError('Failed to load patients')
      }
    } catch {
      setError('Connection error')
    }
    setLoading(false)
  }, [search, statusFilter, page])

  useEffect(() => { loadPatients() }, [loadPatients])

  // Close phase dropdown when clicking outside
  useEffect(() => {
    if (!phaseDropdownPatient) return
    function handleClickOutside() {
      setPhaseDropdownPatient(null)
    }
    document.addEventListener('click', handleClickOutside)
    return () => document.removeEventListener('click', handleClickOutside)
  }, [phaseDropdownPatient])

  function handleSearchChange(value: string) {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => {
      setSearch(value)
      setPage(1)
    }, 300)
  }

  async function handleCreatePatient(e: React.FormEvent) {
    e.preventDefault()
    setCreateLoading(true)
    setCreateError('')
    try {
      const res = await api.request('/api/v1/patients', {
        method: 'POST',
        body: JSON.stringify(newPatient),
      })
      if (res.ok) {
        setShowCreateModal(false)
        setNewPatient({ first_name: '', middle_name: '', last_name: '', date_of_birth: '', gender: '', email: '', phone: '', responsible_party: '', treatment_phase: '', referring_doctor: '', sms_consent: true, email_consent: true })
        loadPatients()
      } else {
        const data = await res.json().catch(() => ({ detail: 'Failed to create patient' }))
        const detail = data.detail
        if (typeof detail === 'string') {
          setCreateError(detail)
        } else if (Array.isArray(detail)) {
          setCreateError(detail.map((e: { msg?: string }) => e.msg || 'Validation error').join(', '))
        } else {
          setCreateError('Failed to create patient')
        }
      }
    } catch {
      setCreateError('Connection error')
    }
    setCreateLoading(false)
  }

  const totalPages = Math.ceil(total / 50)

  async function handleQuickPhaseChange(patientId: string, newPhase: string) {
    // Optimistic update
    setPatients(prev => prev.map(p => p.id === patientId ? { ...p, treatment_phase: newPhase } : p))
    setPhaseDropdownPatient(null)
    try {
      const res = await api.updatePatient(patientId, { treatment_phase: newPhase })
      if (!res.ok) {
        // Revert on failure
        loadPatients()
      }
    } catch {
      loadPatients()
    }
  }

  return (
    <>
        {/* Title + Add */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Patients</h2>
            <p className="text-sm text-gray-500 mt-0.5">{total} patient{total !== 1 ? 's' : ''} total</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-sm font-medium transition-colors shadow-sm">
            <Plus size={16} /> New Patient
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search patients..."
              defaultValue={search}
              onChange={e => handleSearchChange(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
            />
          </div>
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="archived">Archived</option>
            <option value="observation_1">Observation 1</option>
            <option value="observation_2">Observation 2</option>
            <option value="observation_3">Observation 3</option>
            <option value="observation_4">Observation 4</option>
            <option value="pending">Pending</option>
            <option value="retention">Retention</option>
          </select>
        </div>

        {/* Patient List */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="w-10 h-10 bg-gray-200 rounded-full" />
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-24" />
                  </div>
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="py-12 text-center text-red-500 text-sm">{error}</div>
          ) : patients.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              {search ? 'No patients found matching your search' : 'No patients yet'}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {patients.map(patient => (
                <div key={patient.id}>
                  <div className="w-full px-6 py-4 flex items-center gap-4 hover:bg-gray-50/80 transition-colors text-left">
                    <button
                      onClick={() => navigate(`/patients/${patient.id}`)}
                      className="w-10 h-10 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center flex-shrink-0"
                    >
                      <span className="text-sm font-semibold text-blue-700">
                        {patient.first_name[0]}{patient.last_name[0]}
                      </span>
                    </button>
                    <button
                      onClick={() => navigate(`/patients/${patient.id}`)}
                      className="flex-1 min-w-0 text-left"
                    >
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {patient.last_name}, {patient.first_name}
                        {patient.visit_status && VISIT_STATUS_BADGES[patient.visit_status] && (
                          <span className={`ml-2 inline-flex items-center text-[10px] px-1.5 py-0.5 rounded-full font-medium ${VISIT_STATUS_BADGES[patient.visit_status].color}`}>
                            {VISIT_STATUS_BADGES[patient.visit_status].label}
                          </span>
                        )}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                      {/* Specialty badge — Cosmetic and Perio are BACKLOG specialties (moved 2026-07-30).
                         Badge display retained for existing patients who may already have these phases. */}
                      {patient.treatment_phase && ['bonding', 'active', 'finishing', 'retention', 'records', 'pending', 'observation_1', 'observation_2', 'observation_3', 'observation_4'].includes(patient.treatment_phase) ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-teal-100 text-teal-700 font-medium">Ortho</span>
                      ) : patient.treatment_phase && ['cosmetic_consult', 'cosmetic_active'].includes(patient.treatment_phase) ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-pink-100 text-pink-700 font-medium">Cosmetic</span>
                      ) : patient.treatment_phase && ['perio_active', 'perio_maintenance'].includes(patient.treatment_phase) ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-100 text-orange-700 font-medium">Perio</span>
                      ) : patient.treatment_phase === 'complete' ? (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-600 font-medium">Complete</span>
                      ) : (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">General</span>
                      )}
                      {patient.treatment_phase && (
                        <div className="relative">
                          <button
                            onClick={(e) => { e.stopPropagation(); setPhaseDropdownPatient(phaseDropdownPatient === patient.id ? null : patient.id) }}
                            className="text-xs text-gray-500 hover:text-teal-700 hover:bg-teal-50 px-1.5 py-0.5 rounded border border-transparent hover:border-teal-200 transition-colors cursor-pointer"
                            title="Change treatment phase"
                          >
                            {PHASE_LABELS[patient.treatment_phase] || patient.treatment_phase}
                          </button>
                          {phaseDropdownPatient === patient.id && (
                            <div className="absolute top-full left-0 mt-1 z-50 bg-white border border-gray-200 rounded-xl shadow-lg py-1 w-48 max-h-60 overflow-y-auto">
                              {TREATMENT_PHASE_OPTIONS.map(opt => (
                                <button
                                  key={opt.value}
                                  onClick={(e) => { e.stopPropagation(); handleQuickPhaseChange(patient.id, opt.value) }}
                                  className={`w-full text-left px-3 py-1.5 text-xs hover:bg-teal-50 hover:text-teal-700 transition-colors ${patient.treatment_phase === opt.value ? 'bg-teal-50 text-teal-700 font-medium' : 'text-gray-700'}`}
                                >
                                  {opt.label}
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      {patient.treatment_phase && ['active', 'finishing', 'retention'].includes(patient.treatment_phase) && patient.created_at && (() => {
                        const elapsed = Math.floor((Date.now() - new Date(patient.created_at).getTime()) / (1000 * 60 * 60 * 24 * 30.44))
                        const remaining = Math.max(0, 24 - elapsed)
                        const isOver = elapsed > 24
                        return (
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${isOver ? 'bg-red-100 text-red-700 border border-red-200' : 'bg-teal-50 text-teal-700 border border-teal-200'}`}>
                            {isOver ? `${elapsed - 24} mo over` : `${remaining} mo remaining`}
                          </span>
                        )
                      })()}
                      {patient.phone && <span className="text-xs text-gray-400">• {patient.phone}</span>}
                    </div>
                  </button>
                  {patient.status && STATUS_BADGES[patient.status] && (
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGES[patient.status].color}`}>
                      {STATUS_BADGES[patient.status].label}
                    </span>
                  )}
                    {/* Info Button */}
                    <button
                      onClick={(e) => { e.stopPropagation(); setExpandedPatient(expandedPatient === patient.id ? null : patient.id) }}
                      className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
                        expandedPatient === patient.id
                          ? 'bg-blue-100 text-blue-700'
                          : 'hover:bg-gray-100 text-gray-400 hover:text-gray-600'
                      }`}
                      title="View patient info"
                    >
                      <Info size={16} />
                    </button>
                  </div>

                  {/* Expanded Patient Info Panel */}
                  {expandedPatient === patient.id && (
                    <div className="px-6 py-4 bg-blue-50/50 border-t border-blue-100">
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 text-sm">
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">First Name</p>
                          <p className="text-gray-900 mt-0.5">{patient.first_name}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Middle Name</p>
                          <p className="text-gray-900 mt-0.5">{patient.middle_name || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Last Name</p>
                          <p className="text-gray-900 mt-0.5">{patient.last_name}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Date of Birth</p>
                          <p className="text-gray-900 mt-0.5">{patient.date_of_birth ? new Date(patient.date_of_birth + 'T00:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' }) : '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Gender</p>
                          <p className="text-gray-900 mt-0.5 capitalize">{patient.gender?.replace(/_/g, ' ') || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Phone</p>
                          <p className="text-gray-900 mt-0.5">{patient.phone || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Email</p>
                          <p className="text-gray-900 mt-0.5 truncate">{patient.email || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Address</p>
                          <p className="text-gray-900 mt-0.5 truncate">{patient.address || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Referring Doctor</p>
                          <p className="text-gray-900 mt-0.5">{patient.referring_doctor || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Responsible Party</p>
                          <p className="text-gray-900 mt-0.5">{patient.responsible_party || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Status</p>
                          <p className="text-gray-900 mt-0.5 capitalize">{patient.status || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Treatment Phase</p>
                          <p className="text-gray-900 mt-0.5">{PHASE_LABELS[patient.treatment_phase || ''] || patient.treatment_phase || '—'}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Chart #</p>
                          <p className="text-gray-900 mt-0.5 font-mono">{patient.id.slice(0, 8).toUpperCase()}</p>
                        </div>
                      </div>
                      <div className="mt-3 flex justify-between items-center">
                        <button
                          onClick={async (e) => {
                            e.stopPropagation()
                            if (!confirm(`Delete ${patient.first_name} ${patient.last_name}? This cannot be undone.`)) return
                            try {
                              const res = await api.request(`/api/v1/patients/${patient.id}`, { method: 'DELETE' })
                              if (res.ok) {
                                setPatients(prev => prev.filter(p => p.id !== patient.id))
                              }
                            } catch {}
                          }}
                          className="text-xs font-medium text-red-500 hover:text-red-700 hover:bg-red-50 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          Delete Patient
                        </button>
                        <button
                          onClick={() => navigate(`/patients/${patient.id}`)}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
                        >
                          View Full Chart →
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 mt-6">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage(p => p + 1)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-white rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Next
            </button>
          </div>
        )}

        {/* Create Patient Modal */}
        {showCreateModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/40" onClick={() => setShowCreateModal(false)} />
            <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 p-6">
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-semibold text-gray-900">New Patient</h3>
                <button onClick={() => setShowCreateModal(false)} className="p-1 text-gray-400 hover:text-gray-600 transition-colors">
                  <X size={20} />
                </button>
              </div>
              {createError && (
                <div className="mb-4 p-3 rounded-xl bg-red-50 text-red-700 text-sm border border-red-100">{createError}</div>
              )}
              <form onSubmit={handleCreatePatient} className="space-y-4">
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">First Name <span style={{color:"#ef4444"}}>*</span></label>
                    <input
                      type="text"
                      required
                      value={newPatient.first_name}
                      onChange={e => setNewPatient(p => ({ ...p, first_name: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Middle Name</label>
                    <input
                      type="text"
                      value={newPatient.middle_name}
                      onChange={e => setNewPatient(p => ({ ...p, middle_name: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Last Name <span style={{color:"#ef4444"}}>*</span></label>
                    <input
                      type="text"
                      required
                      value={newPatient.last_name}
                      onChange={e => setNewPatient(p => ({ ...p, last_name: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Date of Birth</label>
                    <input
                      type="date"
                      value={newPatient.date_of_birth}
                      onChange={e => setNewPatient(p => ({ ...p, date_of_birth: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Gender</label>
                    <select
                      value={newPatient.gender}
                      onChange={e => setNewPatient(p => ({ ...p, gender: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    >
                      <option value="">Select...</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="non_binary">Non-binary</option>
                      <option value="other">Other</option>
                      <option value="prefer_not_to_say">Prefer not to say</option>
                    </select>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Email</label>
                    <input
                      type="email"
                      value={newPatient.email}
                      onChange={e => setNewPatient(p => ({ ...p, email: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Phone</label>
                    <input
                      type="tel"
                      value={newPatient.phone}
                      onChange={e => setNewPatient(p => ({ ...p, phone: e.target.value }))}
                      className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Responsible Party (Parent/Guardian)</label>
                  <input
                    type="text"
                    value={newPatient.responsible_party}
                    onChange={e => setNewPatient(p => ({ ...p, responsible_party: e.target.value }))}
                    placeholder="Required for patients under 18"
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Patient Type</label>
                  <select
                    value={newPatient.treatment_phase}
                    onChange={e => setNewPatient(p => ({ ...p, treatment_phase: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                  >
                    <option value="">Select type...</option>
                    <optgroup label="🏥 General Dentistry">
                      <option value="new_patient">New Patient</option>
                      <option value="active_gp">Active GP Patient</option>
                      <option value="hygiene_recall">Hygiene / Recall</option>
                      <option value="restorative">Restorative Treatment</option>
                    </optgroup>
                    <optgroup label="🦷 Orthodontics">
                      <option value="consultation">Ortho Consultation</option>
                      <option value="pending">Pending Start</option>
                      <option value="observation_1">Observation 1</option>
                      <option value="observation_2">Observation 2</option>
                      <option value="observation_3">Observation 3</option>
                      <option value="observation_4">Observation 4</option>
                      <option value="records">Records</option>
                      <option value="bonding">Bonding</option>
                      <option value="active">Active Ortho Treatment</option>
                      <option value="finishing">Finishing</option>
                      <option value="retention">Retention</option>
                    </optgroup>
                    {/* BACKLOG: Cosmetic and Periodontics specialties moved to backlog.
                       These optgroups are intentionally removed from new patient creation.
                       Existing patients with cosmetic/perio phases are still displayed correctly.
                       See: Multi-specialty scoping decision 2026-07-30 */}
                    <optgroup label="✅ Complete">
                      <option value="complete">Treatment Complete</option>
                    </optgroup>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Referring Doctor</label>
                  <input
                    type="text"
                    value={newPatient.referring_doctor}
                    onChange={e => setNewPatient(p => ({ ...p, referring_doctor: e.target.value }))}
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                  />
                </div>

                {/* Communication Consent */}
                <div className="pt-3 border-t border-gray-100 space-y-2">
                  <p className="text-xs font-medium text-gray-600 uppercase tracking-wide">Communication Consent</p>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newPatient.sms_consent}
                      onChange={e => setNewPatient(p => ({ ...p, sms_consent: e.target.checked }))}
                      className="rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                    />
                    <span className="text-sm text-gray-700">SMS appointment reminders & notifications</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={newPatient.email_consent}
                      onChange={e => setNewPatient(p => ({ ...p, email_consent: e.target.checked }))}
                      className="rounded border-gray-300 text-teal-600 focus:ring-teal-500"
                    />
                    <span className="text-sm text-gray-700">Email communications & reminders</span>
                  </label>
                  <p className="text-[10px] text-gray-400">Patient can opt out at any time. <a href="/terms" className="underline">Terms & conditions</a></p>
                </div>

                <div className="flex justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createLoading}
                    className="flex items-center gap-2 px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {createLoading && <Loader2 size={14} className="animate-spin" />}
                    {createLoading ? 'Creating...' : 'Create Patient'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
          </>
  )
}
