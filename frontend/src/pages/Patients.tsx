import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Users, Plus, Clock } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  last_name: string
  date_of_birth: string | null
  email: string | null
  phone: string | null
  status: string | null
  treatment_phase: string | null
  referring_doctor: string | null
  created_at: string | null
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  active: { label: 'Active', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  inactive: { label: 'Inactive', color: 'bg-gray-50 text-gray-600 border-gray-200' },
  archived: { label: 'Archived', color: 'bg-red-50 text-red-600 border-red-200' },
}

const PHASE_LABELS: Record<string, string> = {
  consultation: 'Consultation',
  records: 'Records',
  treatment_planning: 'Treatment Planning',
  active_treatment: 'Active Treatment',
  retention: 'Retention',
  completed: 'Completed',
}

export default function Patients() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()
const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)
  const loadPatients = useCallback(async () => {
    setLoading(true)
    const res = await api.getPatients({ search, status: statusFilter, page })
    if (res.ok) {
      const data = await res.json()
      setPatients(data.patients)
      setTotal(data.total)
    }
    setLoading(false)
  }, [search, statusFilter, page])

  useEffect(() => { loadPatients() }, [loadPatients])

  function handleSearchChange(value: string) {
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => {
      setSearch(value)
      setPage(1)
    }, 300)
  }

  const totalPages = Math.ceil(total / 50)

  return (
    <>
        {/* Title + Add */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Patients</h2>
            <p className="text-sm text-gray-500 mt-0.5">{total} patient{total !== 1 ? 's' : ''} total</p>
          </div>
          <button className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-sm font-medium transition-colors shadow-sm">
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
          ) : patients.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              {search ? 'No patients found matching your search' : 'No patients yet'}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {patients.map(patient => (
                <button
                  key={patient.id}
                  onClick={() => navigate(`/patients/${patient.id}`)}
                  className="w-full px-6 py-4 flex items-center gap-4 hover:bg-gray-50/80 transition-colors text-left"
                >
                  <div className="w-10 h-10 bg-gradient-to-br from-blue-100 to-blue-200 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sm font-semibold text-blue-700">
                      {patient.first_name[0]}{patient.last_name[0]}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {patient.last_name}, {patient.first_name}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      {patient.treatment_phase && (
                        <span className="text-xs text-gray-500">{PHASE_LABELS[patient.treatment_phase] || patient.treatment_phase}</span>
                      )}
                      {patient.phone && <span className="text-xs text-gray-400">• {patient.phone}</span>}
                    </div>
                  </div>
                  {patient.status && STATUS_BADGES[patient.status] && (
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGES[patient.status].color}`}>
                      {STATUS_BADGES[patient.status].label}
                    </span>
                  )}
                </button>
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
          </>
  )
}
