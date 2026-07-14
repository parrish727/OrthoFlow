import { useState, useEffect, useCallback, useRef } from 'react'
import { Shield, Search, Plus, CheckCircle, Users, FileText, AlertCircle, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  last_name: string
}

interface InsurancePlan {
  id: string
  patient_id: string
  payer_name: string
  subscriber_id: string
  group_number: string
  plan_type: 'primary' | 'secondary'
  coverage_percentage: number
  benefits_used: number
  benefits_remaining: number
  benefits_max: number
  effective_date: string
  termination_date: string | null
  is_active: boolean
}

interface EligibilityResult {
  plan_id: string
  eligible: boolean
  message: string
  checked_at: string
}

const PLAN_TYPE_BADGES: Record<string, { label: string; color: string }> = {
  primary: { label: 'Primary', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  secondary: { label: 'Secondary', color: 'bg-purple-50 text-purple-700 border-purple-200' },
}

export default function Insurance() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [patientSearch, setPatientSearch] = useState('')
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [showPatientDropdown, setShowPatientDropdown] = useState(false)
  const [plans, setPlans] = useState<InsurancePlan[]>([])
  const [loading, setLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [formLoading, setFormLoading] = useState(false)
  const [eligibilityChecking, setEligibilityChecking] = useState<string | null>(null)
  const [eligibilityResults, setEligibilityResults] = useState<Record<string, EligibilityResult>>({})
const patientDropdownRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Add plan form state
  const [newPayer, setNewPayer] = useState('')
  const [newSubscriberId, setNewSubscriberId] = useState('')
  const [newGroupNumber, setNewGroupNumber] = useState('')
  const [newPlanType, setNewPlanType] = useState<'primary' | 'secondary'>('primary')
  const [newCoverage, setNewCoverage] = useState('80')
  const [newBenefitsMax, setNewBenefitsMax] = useState('')

  useEffect(() => {
    function handleClick(e: MouseEvent) {
            if (patientDropdownRef.current && !patientDropdownRef.current.contains(e.target as Node)) setShowPatientDropdown(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])
  const searchPatients = useCallback(async (query: string) => {
    if (!query.trim()) { setPatients([]); return }
    const res = await api.getPatients({ search: query })
    if (res.ok) {
      const data = await res.json()
      setPatients(data.patients || [])
    }
  }, [])

  function handlePatientSearch(value: string) {
    setPatientSearch(value)
    setShowPatientDropdown(true)
    if (searchTimeout.current) clearTimeout(searchTimeout.current)
    searchTimeout.current = setTimeout(() => searchPatients(value), 300)
  }

  function selectPatient(patient: Patient) {
    setSelectedPatient(patient)
    setPatientSearch(`${patient.last_name}, ${patient.first_name}`)
    setShowPatientDropdown(false)
    setEligibilityResults({})
  }

  const loadPlans = useCallback(async () => {
    if (!selectedPatient) return
    setLoading(true)
    try {
      const res = await api.getInsurancePlans(selectedPatient.id)
      if (res.ok) {
        const data = await res.json()
        setPlans(data.insurance_plans || data.plans || [])
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [selectedPatient])

  useEffect(() => { loadPlans() }, [loadPlans])

  async function handleCheckEligibility(planId: string) {
    setEligibilityChecking(planId)
    try {
      const res = await api.checkEligibility({ plan_id: planId })
      if (res.ok) {
        const data = await res.json()
        setEligibilityResults(prev => ({ ...prev, [planId]: data }))
      }
    } catch {
      // silently handle
    }
    setEligibilityChecking(null)
  }

  async function handleAddPlan(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedPatient) return
    setFormLoading(true)
    try {
      const res = await api.addInsurancePlan({
        patient_id: selectedPatient.id,
        payer_name: newPayer,
        subscriber_id: newSubscriberId,
        group_number: newGroupNumber,
        plan_type: newPlanType,
        coverage_percentage: parseInt(newCoverage, 10),
        benefits_max: newBenefitsMax ? parseFloat(newBenefitsMax) : null,
      })
      if (res.ok) {
        setNewPayer('')
        setNewSubscriberId('')
        setNewGroupNumber('')
        setNewPlanType('primary')
        setNewCoverage('80')
        setNewBenefitsMax('')
        setShowAddForm(false)
        loadPlans()
      }
    } catch {
      // silently handle
    }
    setFormLoading(false)
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
  }

  return (
    <>
        {/* Title */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Insurance Plans</h2>
            <p className="text-sm text-gray-500 mt-0.5">Manage patient insurance & check eligibility</p>
          </div>
        </div>

        {/* Patient Selector */}
        <div className="relative mb-6" ref={patientDropdownRef}>
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search for a patient..."
            value={patientSearch}
            onChange={e => handlePatientSearch(e.target.value)}
            onFocus={() => { if (patients.length > 0) setShowPatientDropdown(true) }}
            className="w-full sm:w-96 pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
          />
          {showPatientDropdown && patients.length > 0 && (
            <div className="absolute top-full mt-1 w-full sm:w-96 bg-white rounded-xl border border-gray-200 shadow-lg py-1 z-30 max-h-60 overflow-y-auto">
              {patients.map(p => (
                <button
                  key={p.id}
                  onClick={() => selectPatient(p)}
                  className="w-full px-4 py-2.5 text-left text-sm hover:bg-gray-50 transition-colors"
                >
                  <span className="font-medium text-gray-900">{p.last_name}, {p.first_name}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {!selectedPatient ? (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-16 text-center">
            <Shield size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-400">Select a patient to view their insurance plans</p>
          </div>
        ) : (
          <>
            {/* Add Plan Button */}
            <div className="flex items-center gap-3 mb-6">
              <button
                onClick={() => setShowAddForm(!showAddForm)}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                <Plus size={16} /> Add Plan
              </button>
            </div>

            {/* Add Plan Form */}
            {showAddForm && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Add Insurance Plan</h3>
                <form onSubmit={handleAddPlan} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <input
                    type="text"
                    placeholder="Payer Name (e.g., Delta Dental)"
                    value={newPayer}
                    onChange={e => setNewPayer(e.target.value)}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Subscriber ID"
                    value={newSubscriberId}
                    onChange={e => setNewSubscriberId(e.target.value)}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <input
                    type="text"
                    placeholder="Group Number"
                    value={newGroupNumber}
                    onChange={e => setNewGroupNumber(e.target.value)}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <select
                    value={newPlanType}
                    onChange={e => setNewPlanType(e.target.value as 'primary' | 'secondary')}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  >
                    <option value="primary">Primary</option>
                    <option value="secondary">Secondary</option>
                  </select>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    placeholder="Coverage % (e.g., 80)"
                    value={newCoverage}
                    onChange={e => setNewCoverage(e.target.value)}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    placeholder="Annual Max Benefits ($)"
                    value={newBenefitsMax}
                    onChange={e => setNewBenefitsMax(e.target.value)}
                    className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                  />
                  <div className="sm:col-span-2 flex justify-end gap-3">
                    <button
                      type="button"
                      onClick={() => setShowAddForm(false)}
                      className="px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={formLoading}
                      className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                    >
                      {formLoading ? 'Adding...' : 'Add Plan'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* Plans List */}
            <div className="space-y-4">
              {loading ? (
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 space-y-4">
                  {[1, 2].map(i => (
                    <div key={i} className="animate-pulse">
                      <div className="h-5 bg-gray-200 rounded w-48 mb-3" />
                      <div className="grid grid-cols-3 gap-4">
                        <div className="h-4 bg-gray-100 rounded" />
                        <div className="h-4 bg-gray-100 rounded" />
                        <div className="h-4 bg-gray-100 rounded" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : plans.length === 0 ? (
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-12 text-center">
                  <Shield size={28} className="mx-auto text-gray-300 mb-3" />
                  <p className="text-sm text-gray-400">No insurance plans on file</p>
                </div>
              ) : (
                plans.map(plan => (
                  <div key={plan.id} className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-base font-semibold text-gray-900">{plan.payer_name}</h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${PLAN_TYPE_BADGES[plan.plan_type]?.color || ''}`}>
                            {PLAN_TYPE_BADGES[plan.plan_type]?.label || plan.plan_type}
                          </span>
                          {!plan.is_active && (
                            <span className="text-xs px-2 py-0.5 rounded-full border font-medium bg-red-50 text-red-600 border-red-200">Inactive</span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500">Subscriber: {plan.subscriber_id} • Group: {plan.group_number}</p>
                      </div>
                      <button
                        onClick={() => handleCheckEligibility(plan.id)}
                        disabled={eligibilityChecking === plan.id}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors disabled:opacity-50"
                      >
                        {eligibilityChecking === plan.id ? (
                          <><Loader2 size={12} className="animate-spin" /> Checking...    </>
  ) : (
                          <><CheckCircle size={12} /> Check Eligibility    </>
  )}
                      </button>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Coverage</p>
                        <p className="text-sm font-medium text-gray-900">{plan.coverage_percentage}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Benefits Used</p>
                        <p className="text-sm font-medium text-gray-900">{formatCurrency(plan.benefits_used)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Remaining</p>
                        <p className="text-sm font-medium text-emerald-600">{formatCurrency(plan.benefits_remaining)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-0.5">Annual Max</p>
                        <p className="text-sm font-medium text-gray-900">{formatCurrency(plan.benefits_max)}</p>
                      </div>
                    </div>

                    {/* Benefits usage bar */}
                    <div className="mt-4">
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full transition-all"
                          style={{ width: `${plan.benefits_max > 0 ? (plan.benefits_used / plan.benefits_max) * 100 : 0}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-400 mt-1">
                        {plan.benefits_max > 0 ? Math.round((plan.benefits_used / plan.benefits_max) * 100) : 0}% of annual max used
                      </p>
                    </div>

                    {/* Eligibility Result */}
                    {eligibilityResults[plan.id] && (
                      <div className={`mt-4 p-3 rounded-xl text-sm flex items-start gap-2 ${eligibilityResults[plan.id].eligible ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                        {eligibilityResults[plan.id].eligible ? (
                          <CheckCircle size={16} className="flex-shrink-0 mt-0.5" />
                        ) : (
                          <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                        )}
                        <span>{eligibilityResults[plan.id].message}</span>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
              </>
  )}
          </>
  )
}
