import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Search, User, FileText, DollarSign, Calculator, CheckCircle,
  Clock, XCircle, MessageSquare, CalendarPlus, Loader2, ChevronRight,
  Percent, CreditCard, AlertCircle
} from 'lucide-react'
import { api } from '../lib/api'

// --- Types ---
interface Patient {
  id: string
  first_name: string
  last_name: string
  date_of_birth: string
  phone?: string
  email?: string
}

interface TreatmentRecommendation {
  phase: string
  notes: string
  provider: string
  date: string
}

type ProposalStatus = 'draft' | 'presented' | 'accepted' | 'declined'
type PaymentOption = 'pay_in_full' | 'monthly' | 'custom'

interface ProposalForm {
  treatment_type: string
  duration_months: number
  total_fee: number
  insurance_estimate: number
  payment_option: PaymentOption
  down_payment: number
  discount_percent: number
  notes: string
  status: ProposalStatus
}

// --- Constants ---
const TREATMENT_TYPES = [
  'Comprehensive Ortho',
  'Limited Ortho',
  'Invisalign Comprehensive',
  'Invisalign Lite',
  'Phase I (Early Treatment)',
  'Phase II',
  'Surgical Ortho',
  'Retainer Only',
]

const STATUS_CONFIG: Record<ProposalStatus, { label: string; color: string; icon: typeof Clock }> = {
  draft: { label: 'Draft', color: 'bg-gray-50 text-gray-700 border-gray-200', icon: FileText },
  presented: { label: 'Presented', color: 'bg-blue-50 text-blue-700 border-blue-200', icon: MessageSquare },
  accepted: { label: 'Accepted', color: 'bg-emerald-50 text-emerald-700 border-emerald-200', icon: CheckCircle },
  declined: { label: 'Declined', color: 'bg-red-50 text-red-600 border-red-200', icon: XCircle },
}

const STATUS_STEPS: ProposalStatus[] = ['draft', 'presented', 'accepted']

function fmt(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0, maximumFractionDigits: 0 }).format(n)
}

// --- Main Component ---
export default function TCProposal() {
  // Patient search
  const [searchQuery, setSearchQuery] = useState('')
  const [patients, setPatients] = useState<Patient[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [showDropdown, setShowDropdown] = useState(false)

  // Doctor recommendation
  const [recommendation, setRecommendation] = useState<TreatmentRecommendation | null>(null)
  const [recLoading, setRecLoading] = useState(false)

  // Proposal form
  const [form, setForm] = useState<ProposalForm>({
    treatment_type: TREATMENT_TYPES[0],
    duration_months: 18,
    total_fee: 5500,
    insurance_estimate: 1500,
    payment_option: 'monthly',
    down_payment: 500,
    discount_percent: 5,
    notes: '',
    status: 'draft',
  })

  // UI state
  const [saving, setSaving] = useState(false)
  const [showScheduleModal, setShowScheduleModal] = useState(false)

  // --- Computed values ---
  const patientResponsibility = useMemo(
    () => form.total_fee - form.insurance_estimate,
    [form.total_fee, form.insurance_estimate]
  )

  const payInFullAmount = useMemo(
    () => patientResponsibility * (1 - form.discount_percent / 100),
    [patientResponsibility, form.discount_percent]
  )

  const payInFullSavings = useMemo(
    () => patientResponsibility - payInFullAmount,
    [patientResponsibility, payInFullAmount]
  )

  const monthlyAmount = useMemo(() => {
    if (form.duration_months <= 0) return 0
    if (form.payment_option === 'custom') {
      const remaining = patientResponsibility - form.down_payment
      return remaining > 0 ? Math.ceil(remaining / form.duration_months) : 0
    }
    return Math.ceil(patientResponsibility / form.duration_months)
  }, [patientResponsibility, form.duration_months, form.down_payment, form.payment_option])

  // --- Patient search ---
  const searchPatients = useCallback(async (query: string) => {
    if (query.length < 2) { setPatients([]); return }
    setSearchLoading(true)
    try {
      const res = await api.getPatients({ search: query })
      if (res.ok) {
        const data = await res.json()
        setPatients(data.patients || [])
      }
    } catch { /* silently handle */ }
    setSearchLoading(false)
  }, [])

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (searchQuery.length >= 2) {
        searchPatients(searchQuery)
        setShowDropdown(true)
      } else {
        setShowDropdown(false)
      }
    }, 300)
    return () => clearTimeout(timeout)
  }, [searchQuery, searchPatients])

  // --- Load doctor recommendation when patient selected ---
  useEffect(() => {
    if (!selectedPatient) { setRecommendation(null); return }
    setRecLoading(true)
    async function loadRec() {
      try {
        const res = await api.getPatientNotes(selectedPatient!.id)
        if (res.ok) {
          const data = await res.json()
          const notes = data.notes || []
          // Find the most recent treatment plan note
          const planNote = notes.find((n: { note_text: string }) =>
            n.note_text?.toLowerCase().includes('treatment') ||
            n.note_text?.toLowerCase().includes('recommend')
          )
          if (planNote) {
            setRecommendation({
              phase: 'Phase I',
              notes: planNote.note_text,
              provider: planNote.provider || 'Dr.',
              date: planNote.created_at || new Date().toISOString(),
            })
          } else {
            setRecommendation({ phase: 'Comprehensive', notes: 'No treatment notes found — consult with doctor.', provider: '', date: '' })
          }
        }
      } catch { /* silently handle */ }
      setRecLoading(false)
    }
    loadRec()
  }, [selectedPatient])

  function selectPatient(patient: Patient) {
    setSelectedPatient(patient)
    setSearchQuery(`${patient.first_name} ${patient.last_name}`)
    setShowDropdown(false)
  }

  function updateForm(updates: Partial<ProposalForm>) {
    setForm(prev => ({ ...prev, ...updates }))
  }

  async function saveProposal() {
    if (!selectedPatient) return
    setSaving(true)
    try {
      await api.request('/api/v1/tc-proposals', {
        method: 'POST',
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          treatment_type: form.treatment_type,
          duration_months: form.duration_months,
          total_fee: form.total_fee,
          insurance_estimate: form.insurance_estimate,
          patient_responsibility: patientResponsibility,
          payment_option: form.payment_option,
          down_payment: form.down_payment,
          monthly_amount: monthlyAmount,
          discount_percent: form.discount_percent,
          notes: form.notes,
          status: form.status,
        }),
      })
    } catch { /* silently handle */ }
    setSaving(false)
  }

  async function markAccepted() {
    updateForm({ status: 'accepted' })
    await saveProposal()
    setShowScheduleModal(true)
  }

  // --- Render ---
  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Treatment Proposal</h2>
        <p className="text-sm text-gray-500 mt-0.5">Build and present treatment proposals to patients</p>
      </div>

      {/* Status Progress Indicator */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between">
          {STATUS_STEPS.map((step, idx) => {
            const cfg = STATUS_CONFIG[step]
            const Icon = cfg.icon
            const isActive = form.status === step
            const isPast = STATUS_STEPS.indexOf(form.status) > idx
            const isDeclined = form.status === 'declined'
            return (
              <div key={step} className="flex items-center flex-1">
                <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium ${
                  isActive ? cfg.color : isPast ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-gray-50 text-gray-400 border-gray-100'
                } ${isDeclined && step !== 'draft' ? 'opacity-50' : ''}`}>
                  <Icon size={14} />
                  {cfg.label}
                </div>
                {idx < STATUS_STEPS.length - 1 && (
                  <ChevronRight size={16} className="mx-2 text-gray-300 flex-shrink-0" />
                )}
              </div>
            )
          })}
          {form.status === 'declined' && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border bg-red-50 text-red-600 border-red-200 text-sm font-medium ml-2">
              <XCircle size={14} /> Declined
            </div>
          )}
        </div>
      </div>

      {/* Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* LEFT COLUMN — Patient Info + Proposal Form (3/5) */}
        <div className="lg:col-span-3 space-y-6">
          {/* Patient Search Card */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
            <div className="flex items-center gap-2 mb-3">
              <User size={16} className="text-teal-600" />
              <h3 className="text-sm font-semibold text-gray-900">Select Patient</h3>
            </div>
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search by name..."
                value={searchQuery}
                onChange={e => { setSearchQuery(e.target.value); if (!e.target.value) setSelectedPatient(null) }}
                className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
              />
              {searchLoading && <Loader2 size={16} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 animate-spin" />}
              {showDropdown && patients.length > 0 && (
                <div className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
                  {patients.map(p => (
                    <button
                      key={p.id}
                      onClick={() => selectPatient(p)}
                      className="w-full text-left px-4 py-2.5 hover:bg-teal-50 text-sm flex items-center gap-3 border-b border-gray-50 last:border-0"
                    >
                      <div className="w-7 h-7 rounded-full bg-teal-100 flex items-center justify-center text-xs font-medium text-teal-700">
                        {p.first_name[0]}{p.last_name[0]}
                      </div>
                      <div>
                        <span className="font-medium text-gray-900">{p.first_name} {p.last_name}</span>
                        {p.date_of_birth && <span className="text-gray-400 ml-2">DOB: {p.date_of_birth}</span>}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
            {selectedPatient && (
              <div className="mt-3 p-3 bg-teal-50/50 rounded-xl border border-teal-100">
                <p className="text-sm font-medium text-teal-800">{selectedPatient.first_name} {selectedPatient.last_name}</p>
                <p className="text-xs text-teal-600 mt-0.5">DOB: {selectedPatient.date_of_birth || 'N/A'} {selectedPatient.phone ? `• ${selectedPatient.phone}` : ''}</p>
              </div>
            )}
          </div>

          {/* Doctor Recommendation Card */}
          {selectedPatient && (
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-3">
                <FileText size={16} className="text-teal-600" />
                <h3 className="text-sm font-semibold text-gray-900">Doctor&apos;s Recommendation</h3>
              </div>
              {recLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-400"><Loader2 size={14} className="animate-spin" /> Loading...</div>
              ) : recommendation ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium bg-teal-100 text-teal-700 px-2 py-0.5 rounded-full">{recommendation.phase}</span>
                    {recommendation.provider && <span className="text-xs text-gray-500">{recommendation.provider}</span>}
                    {recommendation.date && <span className="text-xs text-gray-400">{new Date(recommendation.date).toLocaleDateString()}</span>}
                  </div>
                  <p className="text-sm text-gray-700 leading-relaxed">{recommendation.notes}</p>
                </div>
              ) : (
                <p className="text-sm text-gray-400">No treatment recommendation on file</p>
              )}
            </div>
          )}

          {/* Proposal Form Card */}
          {selectedPatient && (
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
              <div className="flex items-center gap-2 mb-4">
                <Calculator size={16} className="text-teal-600" />
                <h3 className="text-sm font-semibold text-gray-900">Treatment Proposal</h3>
              </div>

              <div className="space-y-4">
                {/* Treatment Type */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Treatment Type</label>
                  <select
                    value={form.treatment_type}
                    onChange={e => updateForm({ treatment_type: e.target.value })}
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 bg-white"
                  >
                    {TREATMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>

                {/* Duration */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Estimated Duration (months)</label>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={form.duration_months}
                    onChange={e => updateForm({ duration_months: parseInt(e.target.value) || 1 })}
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                  />
                </div>

                {/* Fee row */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Total Fee</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        min={0}
                        step={100}
                        value={form.total_fee}
                        onChange={e => updateForm({ total_fee: parseFloat(e.target.value) || 0 })}
                        className="w-full pl-8 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Insurance Estimate</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        min={0}
                        step={100}
                        value={form.insurance_estimate}
                        onChange={e => updateForm({ insurance_estimate: parseFloat(e.target.value) || 0 })}
                        className="w-full pl-8 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                      />
                    </div>
                  </div>
                </div>

                {/* Patient Responsibility (read-only calculated) */}
                <div className="p-3 bg-gray-50 rounded-xl border border-gray-100">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-gray-600">Patient Responsibility</span>
                    <span className="text-lg font-bold text-gray-900">{fmt(patientResponsibility)}</span>
                  </div>
                </div>

                {/* Payment Option */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-2">Payment Option</label>
                  <div className="grid grid-cols-3 gap-2">
                    {(['pay_in_full', 'monthly', 'custom'] as PaymentOption[]).map(opt => (
                      <button
                        key={opt}
                        onClick={() => updateForm({ payment_option: opt })}
                        className={`px-3 py-2 rounded-xl text-xs font-medium border transition-colors ${
                          form.payment_option === opt
                            ? 'bg-teal-50 border-teal-300 text-teal-700'
                            : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                        }`}
                      >
                        {opt === 'pay_in_full' ? 'Pay in Full' : opt === 'monthly' ? 'Monthly' : 'Custom'}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Discount percent (for pay in full) */}
                {form.payment_option === 'pay_in_full' && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Pay-in-Full Discount (%)</label>
                    <div className="relative">
                      <Percent size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        min={0}
                        max={25}
                        value={form.discount_percent}
                        onChange={e => updateForm({ discount_percent: parseFloat(e.target.value) || 0 })}
                        className="w-full pl-8 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                      />
                    </div>
                  </div>
                )}

                {/* Down payment (for custom) */}
                {form.payment_option === 'custom' && (
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Down Payment</label>
                    <div className="relative">
                      <DollarSign size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="number"
                        min={0}
                        step={50}
                        value={form.down_payment}
                        onChange={e => updateForm({ down_payment: parseFloat(e.target.value) || 0 })}
                        className="w-full pl-8 pr-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400"
                      />
                    </div>
                  </div>
                )}

                {/* TC Notes */}
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">TC Notes</label>
                  <textarea
                    rows={3}
                    placeholder="Notes about the conversation, patient concerns, follow-up needed..."
                    value={form.notes}
                    onChange={e => updateForm({ notes: e.target.value })}
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-400 resize-none"
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN — Fee Summary + Payment Calculator (2/5) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Fee Summary Card */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 sticky top-6">
            <div className="flex items-center gap-2 mb-4">
              <DollarSign size={16} className="text-teal-600" />
              <h3 className="text-sm font-semibold text-gray-900">Fee Summary</h3>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Total Fee</span>
                <span className="font-medium text-gray-900">{fmt(form.total_fee)}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-gray-600">Insurance Estimate</span>
                <span className="font-medium text-emerald-600">- {fmt(form.insurance_estimate)}</span>
              </div>
              <div className="border-t border-gray-100 pt-3 flex justify-between items-center">
                <span className="text-sm font-medium text-gray-700">Patient Owes</span>
                <span className="text-xl font-bold text-gray-900">{fmt(patientResponsibility)}</span>
              </div>
            </div>

            {/* Payment Calculator */}
            <div className="mt-5 pt-5 border-t border-gray-100">
              <div className="flex items-center gap-2 mb-3">
                <CreditCard size={14} className="text-teal-600" />
                <h4 className="text-xs font-semibold text-gray-700 uppercase tracking-wide">Payment Options</h4>
              </div>

              <div className="space-y-3">
                {/* Option A: Pay in Full */}
                <div className={`p-3 rounded-xl border transition-colors ${
                  form.payment_option === 'pay_in_full' ? 'border-teal-300 bg-teal-50/50' : 'border-gray-100 bg-gray-50/50'
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-700">Option A: Pay in Full</span>
                    <span className="text-xs bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded-full font-medium">Save {fmt(payInFullSavings)}</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900">{fmt(payInFullAmount)}</p>
                  <p className="text-xs text-gray-500">{form.discount_percent}% discount applied</p>
                </div>

                {/* Option B: Monthly */}
                <div className={`p-3 rounded-xl border transition-colors ${
                  form.payment_option === 'monthly' ? 'border-teal-300 bg-teal-50/50' : 'border-gray-100 bg-gray-50/50'
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-700">Option B: Monthly Payments</span>
                  </div>
                  <p className="text-lg font-bold text-gray-900">{fmt(monthlyAmount)}<span className="text-sm font-normal text-gray-500">/mo</span></p>
                  <p className="text-xs text-gray-500">{form.duration_months} months × {fmt(monthlyAmount)} = {fmt(monthlyAmount * form.duration_months)}</p>
                </div>

                {/* Option C: Custom */}
                <div className={`p-3 rounded-xl border transition-colors ${
                  form.payment_option === 'custom' ? 'border-teal-300 bg-teal-50/50' : 'border-gray-100 bg-gray-50/50'
                }`}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-gray-700">Option C: Custom</span>
                  </div>
                  <p className="text-sm text-gray-700">
                    <span className="font-bold">{fmt(form.down_payment)}</span> down + <span className="font-bold">{fmt(monthlyAmount)}</span>/mo × {form.duration_months} mo
                  </p>
                  <p className="text-xs text-gray-500">Total: {fmt(form.down_payment + monthlyAmount * form.duration_months)}</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="mt-5 pt-5 border-t border-gray-100 space-y-2">
              {form.status === 'draft' && (
                <>
                  <button
                    onClick={() => { updateForm({ status: 'presented' }); saveProposal() }}
                    disabled={!selectedPatient || saving}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 text-white rounded-xl text-sm font-medium hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <MessageSquare size={14} />}
                    Mark as Presented
                  </button>
                  <button
                    onClick={saveProposal}
                    disabled={!selectedPatient || saving}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    Save Draft
                  </button>
                </>
              )}
              {form.status === 'presented' && (
                <>
                  <button
                    onClick={markAccepted}
                    disabled={saving}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
                  >
                    {saving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                    Mark as Accepted
                  </button>
                  <button
                    onClick={() => { updateForm({ status: 'declined' }); saveProposal() }}
                    disabled={saving}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-red-200 text-red-600 rounded-xl text-sm font-medium hover:bg-red-50 disabled:opacity-50 transition-colors"
                  >
                    <XCircle size={14} /> Mark as Declined
                  </button>
                </>
              )}
              {form.status === 'accepted' && (
                <div className="flex items-center gap-2 p-3 bg-emerald-50 rounded-xl border border-emerald-200">
                  <CheckCircle size={16} className="text-emerald-600" />
                  <span className="text-sm font-medium text-emerald-700">Proposal Accepted!</span>
                </div>
              )}
              {form.status === 'declined' && (
                <div className="flex items-center gap-2 p-3 bg-red-50 rounded-xl border border-red-200">
                  <AlertCircle size={16} className="text-red-500" />
                  <span className="text-sm font-medium text-red-600">Proposal Declined</span>
                </div>
              )}
              {/* Print PDF — always available */}
              <button
                onClick={() => window.print()}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors mt-2"
              >
                <FileText size={14} /> Print PDF
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Schedule First Appointment Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-6 w-full max-w-md mx-4">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                <CalendarPlus size={20} className="text-emerald-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Schedule Start Appointment</h3>
                <p className="text-sm text-gray-500">Patient accepted the treatment proposal</p>
              </div>
            </div>
            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-100 mb-4">
              <p className="text-sm text-emerald-800">
                <span className="font-medium">{selectedPatient?.first_name} {selectedPatient?.last_name}</span> accepted {form.treatment_type} treatment.
              </p>
              <p className="text-xs text-emerald-600 mt-1">
                {form.payment_option === 'pay_in_full'
                  ? `Paying in full: ${fmt(payInFullAmount)}`
                  : form.payment_option === 'custom'
                    ? `${fmt(form.down_payment)} down + ${fmt(monthlyAmount)}/mo`
                    : `Monthly: ${fmt(monthlyAmount)}/mo × ${form.duration_months} months`
                }
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => {
                  setShowScheduleModal(false)
                  window.location.href = '/schedule'
                }}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-teal-600 text-white rounded-xl text-sm font-medium hover:bg-teal-700 transition-colors"
              >
                <CalendarPlus size={14} /> Go to Schedule
              </button>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2.5 border border-gray-200 text-gray-700 rounded-xl text-sm font-medium hover:bg-gray-50 transition-colors"
              >
                Later
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
