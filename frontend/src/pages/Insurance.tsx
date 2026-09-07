import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  Shield, Search, CheckCircle, AlertCircle, Loader2, ChevronRight, ChevronDown,
  FileText, Receipt, CreditCard, UserCircle, Sparkles,
} from 'lucide-react'
import { api } from '../lib/api'

interface RosterEntry {
  patient_id: string
  first_name: string
  last_name: string
  treatment_phase: string | null
  has_insurance: boolean
  payer_name: string | null
  plan_name: string | null
  plan_type: string | null
  subscriber_id: string | null
  eligibility_status: string | null
  ortho_remaining: number | null
  balance: number
}

interface InsurancePlan {
  id: string
  patient_id: string
  payer_name: string
  plan_name: string | null
  subscriber_id: string
  group_number: string
  plan_type: string
  coverage_type: string
  ortho_coverage_pct: number | null
  annual_max: number | null
  annual_used: number | null
  ortho_lifetime_max: number | null
  ortho_lifetime_used: number | null
  deductible_amount: number | null
  deductible_met: number | null
  copay_amount: number | null
  effective_date: string | null
  termination_date: string | null
  is_active: boolean
}

interface Alert { severity: string; code: string; message: string }
interface EligibilityResult {
  eligible: boolean
  coverage_active: boolean
  plan_name: string | null
  remaining_benefit: number | null
  ortho_remaining: number | null
  copay: number | null
  deductible_remaining: number | null
  source: string
  alerts: Alert[]
  errors: string[]
}

function money(n: number | null | undefined): string {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

const PHASE_COLORS: Record<string, string> = {
  consultation: 'bg-yellow-100 text-yellow-700', records: 'bg-sky-100 text-sky-700',
  active: 'bg-green-100 text-green-700', bonding: 'bg-emerald-100 text-emerald-700',
  observation_1: 'bg-blue-100 text-blue-700', finishing: 'bg-violet-100 text-violet-700',
  retention: 'bg-teal-100 text-teal-700',
}

export default function Insurance() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [roster, setRoster] = useState<RosterEntry[]>([])
  const [rosterMeta, setRosterMeta] = useState<{ count: number; with_insurance: number }>({ count: 0, with_insurance: 0 })
  const [loadingRoster, setLoadingRoster] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [plans, setPlans] = useState<Record<string, InsurancePlan[]>>({})
  const [loadingPlans, setLoadingPlans] = useState<string | null>(null)
  const [eligibility, setEligibility] = useState<Record<string, EligibilityResult>>({})
  const [checking, setChecking] = useState<string | null>(null)

  // Load the full roster on arrival — no search gate.
  const loadRoster = useCallback(async () => {
    setLoadingRoster(true)
    try {
      const res = await api.getInsuranceRoster()
      if (res.ok) {
        const data = await res.json()
        setRoster(data.patients || [])
        setRosterMeta({ count: data.count || 0, with_insurance: data.with_insurance || 0 })
      }
    } catch { /* handled by empty state */ }
    setLoadingRoster(false)
  }, [])

  useEffect(() => { loadRoster() }, [loadRoster])

  // Deep-link support: ?patient_id=... auto-expands that patient.
  useEffect(() => {
    const pid = searchParams.get('patient_id')
    if (pid && roster.length > 0) toggleExpand(pid)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roster])

  async function toggleExpand(patientId: string) {
    if (expandedId === patientId) { setExpandedId(null); return }
    setExpandedId(patientId)
    if (!plans[patientId]) {
      setLoadingPlans(patientId)
      try {
        const res = await api.getInsurancePlans(patientId)
        if (res.ok) {
          const data = await res.json()
          setPlans(prev => ({ ...prev, [patientId]: data.insurance_plans || data.plans || [] }))
        }
      } catch { /* handled */ }
      setLoadingPlans(null)
    }
  }

  async function checkEligibility(patientId: string, planId: string) {
    setChecking(planId)
    try {
      const res = await api.checkEligibility({ patient_id: patientId, subscriber_plan_id: planId })
      if (res.ok) {
        const data = await res.json()
        setEligibility(prev => ({ ...prev, [planId]: data }))
      }
    } catch { /* handled */ }
    setChecking(null)
  }

  const filtered = roster.filter(r => {
    if (!filter.trim()) return true
    const q = filter.toLowerCase()
    return `${r.first_name} ${r.last_name}`.toLowerCase().includes(q)
      || (r.payer_name || '').toLowerCase().includes(q)
      || (r.subscriber_id || '').toLowerCase().includes(q)
  })

  return (
    <div data-testid="insurance-page">
      {/* Title */}
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Insurance</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {rosterMeta.count} patients · {rosterMeta.with_insurance} with coverage on file
          </p>
        </div>
      </div>

      {/* Optional filter — roster is visible without it */}
      <div className="relative mb-4 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          data-testid="insurance-filter"
          type="text"
          placeholder="Filter by patient, payer, or member ID…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300"
        />
      </div>

      {/* Roster — all patients in plain sight */}
      {loadingRoster ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-16 bg-white rounded-xl border border-gray-200/70 animate-pulse" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-16 text-center">
          <Shield size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No patients match “{filter}”.</p>
        </div>
      ) : (
        <div className="space-y-2" data-testid="insurance-roster">
          {filtered.map(r => {
            const isOpen = expandedId === r.patient_id
            return (
              <div key={r.patient_id} className="bg-white rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
                {/* Roster row — click to expand */}
                <button
                  data-testid={`roster-row-${r.patient_id}`}
                  onClick={() => toggleExpand(r.patient_id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  {isOpen ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{r.last_name}, {r.first_name}</span>
                      {r.treatment_phase && (
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${PHASE_COLORS[r.treatment_phase] || 'bg-gray-100 text-gray-600'}`}>
                          {r.treatment_phase.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 truncate">
                      {r.has_insurance ? `${r.payer_name} · ${r.plan_type}` : 'No insurance on file'}
                    </p>
                  </div>
                  <div className="hidden sm:block text-right shrink-0">
                    <p className="text-xs text-gray-400">Ortho remaining</p>
                    <p className="text-sm font-medium text-emerald-600">{money(r.ortho_remaining)}</p>
                  </div>
                  <div className="hidden md:block text-right shrink-0 w-24">
                    <p className="text-xs text-gray-400">Balance</p>
                    <p className={`text-sm font-medium ${r.balance > 0 ? 'text-amber-600' : 'text-gray-900'}`}>{money(r.balance)}</p>
                  </div>
                </button>

                {/* Expanded patient panel */}
                {isOpen && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50/50" data-testid={`patient-panel-${r.patient_id}`}>
                    {/* Quick-link tabs to related sections for this patient */}
                    <div className="flex flex-wrap gap-2 mb-4">
                      <QuickLink icon={UserCircle} label="Patient Record" onClick={() => navigate(`/patients/${r.patient_id}`)} />
                      <QuickLink icon={FileText} label="Claims" onClick={() => navigate(`/claims?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={Receipt} label="Ledger" onClick={() => navigate(`/ledger?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={CreditCard} label="Payments" onClick={() => navigate(`/payments?patient_id=${r.patient_id}`)} />
                    </div>

                    {loadingPlans === r.patient_id ? (
                      <div className="flex items-center gap-2 text-sm text-gray-400 py-4">
                        <Loader2 size={14} className="animate-spin" /> Loading plans…
                      </div>
                    ) : (plans[r.patient_id] || []).length === 0 ? (
                      <p className="text-sm text-gray-400 py-2">No insurance plans on file for this patient.</p>
                    ) : (
                      <div className="space-y-3">
                        {plans[r.patient_id].map(plan => {
                          const elig = eligibility[plan.id]
                          const orthoRemaining = (plan.ortho_lifetime_max ?? 0) - (plan.ortho_lifetime_used ?? 0)
                          const annualRemaining = (plan.annual_max ?? 0) - (plan.annual_used ?? 0)
                          return (
                            <div key={plan.id} className="bg-white rounded-xl border border-gray-200/80 p-4">
                              <div className="flex items-start justify-between mb-3">
                                <div>
                                  <div className="flex items-center gap-2">
                                    <h4 className="font-semibold text-gray-900">{plan.payer_name}</h4>
                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 font-medium">
                                      {plan.coverage_type}
                                    </span>
                                  </div>
                                  <p className="text-xs text-gray-500 mt-0.5">
                                    {plan.plan_name} · Member {plan.subscriber_id}{plan.group_number ? ` · Group ${plan.group_number}` : ''}
                                  </p>
                                </div>
                                <button
                                  data-testid={`check-eligibility-${plan.id}`}
                                  onClick={() => checkEligibility(r.patient_id, plan.id)}
                                  disabled={checking === plan.id}
                                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors disabled:opacity-50 shrink-0"
                                >
                                  {checking === plan.id
                                    ? <><Loader2 size={12} className="animate-spin" /> Checking…</>
                                    : <><CheckCircle size={12} /> Check Eligibility</>}
                                </button>
                              </div>

                              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                <Metric label="Ortho Coverage" value={`${plan.ortho_coverage_pct ?? 0}%`} />
                                <Metric label="Ortho Remaining" value={money(orthoRemaining)} accent="emerald" />
                                <Metric label="Annual Remaining" value={money(annualRemaining)} />
                                <Metric label="Copay" value={money(plan.copay_amount)} />
                              </div>

                              {/* Eligibility result + precognitive alerts */}
                              {elig && (
                                <div className="mt-3 space-y-2" data-testid={`eligibility-result-${plan.id}`}>
                                  <div className={`p-2.5 rounded-lg text-sm flex items-center gap-2 ${elig.coverage_active ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}>
                                    {elig.coverage_active ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
                                    <span>{elig.coverage_active ? 'Coverage active' : 'Coverage inactive'}</span>
                                    <span className="ml-auto text-xs opacity-70">
                                      {elig.source === 'stedi_live' ? 'via Stedi (live)' : 'stored benefits'}
                                    </span>
                                  </div>
                                  {(elig.alerts || []).map((a, i) => (
                                    <div key={i} className={`p-2.5 rounded-lg text-sm flex items-start gap-2 ${
                                      a.severity === 'critical' ? 'bg-red-50 text-red-700'
                                      : a.severity === 'warning' ? 'bg-amber-50 text-amber-700'
                                      : 'bg-sky-50 text-sky-700'}`}>
                                      <Sparkles size={14} className="shrink-0 mt-0.5" />
                                      <span>{a.message}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function QuickLink({ icon: Icon, label, onClick }: { icon: typeof FileText; label: string; onClick: () => void }) {
  return (
    <button
      data-testid={`quicklink-${label.toLowerCase().replace(/\s+/g, '-')}`}
      onClick={onClick}
      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-700 border border-gray-200 rounded-full hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
    >
      <Icon size={13} /> {label}
    </button>
  )
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div>
      <p className="text-xs text-gray-500 mb-0.5">{label}</p>
      <p className={`text-sm font-medium ${accent === 'emerald' ? 'text-emerald-600' : 'text-gray-900'}`}>{value}</p>
    </div>
  )
}
