import { useState, useEffect, useCallback, useRef } from 'react'
import { Search, Plus, DollarSign, Users, CreditCard, FileText } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  last_name: string
}

interface LedgerEntry {
  id: string
  date: string
  description: string
  type: 'charge' | 'payment' | 'adjustment' | 'insurance_payment'
  amount: number
  running_balance: number
}

interface LedgerSummary {
  total_charges: number
  total_payments: number
  total_adjustments: number
  current_balance: number
}

const TYPE_BADGES: Record<string, { label: string; color: string }> = {
  charge: { label: 'Charge', color: 'bg-red-50 text-red-700 border-red-200' },
  payment: { label: 'Payment', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  adjustment: { label: 'Adjustment', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  insurance_payment: { label: 'Insurance', color: 'bg-blue-50 text-blue-700 border-blue-200' },
}

export default function Ledger() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [patientSearch, setPatientSearch] = useState('')
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null)
  const [showPatientDropdown, setShowPatientDropdown] = useState(false)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [summary, setSummary] = useState<LedgerSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [showChargeForm, setShowChargeForm] = useState(false)
  const [showPaymentForm, setShowPaymentForm] = useState(false)
  const [formLoading, setFormLoading] = useState(false)
const patientDropdownRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Charge form state
  const [chargeDesc, setChargeDesc] = useState('')
  const [chargeAmount, setChargeAmount] = useState('')

  // Payment form state
  const [paymentDesc, setPaymentDesc] = useState('')
  const [paymentAmount, setPaymentAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('cash')

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
  }

  const loadLedger = useCallback(async () => {
    if (!selectedPatient) return
    setLoading(true)
    try {
      const [entriesRes, summaryRes] = await Promise.all([
        api.getLedger(selectedPatient.id),
        api.getLedgerSummary(selectedPatient.id),
      ])
      if (entriesRes.ok) {
        const data = await entriesRes.json()
        setEntries(data.entries || data || [])
      }
      if (summaryRes.ok) {
        const data = await summaryRes.json()
        setSummary(data)
      }
    } catch {
      // silently handle — entries will remain empty
    }
    setLoading(false)
  }, [selectedPatient])

  useEffect(() => { loadLedger() }, [loadLedger])

  async function handlePostCharge(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedPatient || !chargeDesc || !chargeAmount) return
    setFormLoading(true)
    try {
      const res = await api.postLedgerEntry({
        patient_id: selectedPatient.id,
        type: 'charge',
        description: chargeDesc,
        amount: parseFloat(chargeAmount),
      })
      if (res.ok) {
        setChargeDesc('')
        setChargeAmount('')
        setShowChargeForm(false)
        loadLedger()
      }
    } catch {
      // silently handle
    }
    setFormLoading(false)
  }

  async function handleRecordPayment(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedPatient || !paymentDesc || !paymentAmount) return
    setFormLoading(true)
    try {
      const res = await api.postLedgerEntry({
        patient_id: selectedPatient.id,
        type: 'payment',
        description: paymentDesc,
        amount: parseFloat(paymentAmount),
        payment_method: paymentMethod,
      })
      if (res.ok) {
        setPaymentDesc('')
        setPaymentAmount('')
        setPaymentMethod('cash')
        setShowPaymentForm(false)
        loadLedger()
      }
    } catch {
      // silently handle
    }
    setFormLoading(false)
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <>
        {/* Title */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Patient Ledger</h2>
            <p className="text-sm text-gray-500 mt-0.5">Financial transactions & balances</p>
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
            <DollarSign size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-400">Select a patient to view their financial ledger</p>
          </div>
        ) : (
          <>
            {/* Summary Card */}
            {summary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
                  <p className="text-xs text-gray-500 mb-1">Total Charges</p>
                  <p className="text-lg font-semibold text-gray-900">{formatCurrency(summary.total_charges)}</p>
                </div>
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
                  <p className="text-xs text-gray-500 mb-1">Total Payments</p>
                  <p className="text-lg font-semibold text-emerald-600">{formatCurrency(summary.total_payments)}</p>
                </div>
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
                  <p className="text-xs text-gray-500 mb-1">Adjustments</p>
                  <p className="text-lg font-semibold text-amber-600">{formatCurrency(summary.total_adjustments)}</p>
                </div>
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
                  <p className="text-xs text-gray-500 mb-1">Current Balance</p>
                  <p className={`text-lg font-semibold ${summary.current_balance > 0 ? 'text-red-600' : 'text-gray-900'}`}>
                    {formatCurrency(summary.current_balance)}
                  </p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-3 mb-6">
              <button
                onClick={() => { setShowChargeForm(!showChargeForm); setShowPaymentForm(false) }}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                <Plus size={16} /> Post Charge
              </button>
              <button
                onClick={() => { setShowPaymentForm(!showPaymentForm); setShowChargeForm(false) }}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                <CreditCard size={16} /> Record Payment
              </button>
            </div>

            {/* Post Charge Form */}
            {showChargeForm && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Post Charge</h3>
                <form onSubmit={handlePostCharge} className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="text"
                    placeholder="Description (e.g., Bracket placement)"
                    value={chargeDesc}
                    onChange={e => setChargeDesc(e.target.value)}
                    className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="Amount"
                    value={chargeAmount}
                    onChange={e => setChargeAmount(e.target.value)}
                    className="w-full sm:w-32 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <button
                    type="submit"
                    disabled={formLoading}
                    className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {formLoading ? 'Posting...' : 'Post'}
                  </button>
                </form>
              </div>
            )}

            {/* Record Payment Form */}
            {showPaymentForm && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
                <h3 className="text-sm font-semibold text-gray-900 mb-4">Record Payment</h3>
                <form onSubmit={handleRecordPayment} className="flex flex-col sm:flex-row gap-3">
                  <input
                    type="text"
                    placeholder="Description"
                    value={paymentDesc}
                    onChange={e => setPaymentDesc(e.target.value)}
                    className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="Amount"
                    value={paymentAmount}
                    onChange={e => setPaymentAmount(e.target.value)}
                    className="w-full sm:w-32 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                    required
                  />
                  <select
                    value={paymentMethod}
                    onChange={e => setPaymentMethod(e.target.value)}
                    className="w-full sm:w-36 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                  >
                    <option value="cash">Cash</option>
                    <option value="check">Check</option>
                    <option value="credit_card">Credit Card</option>
                    <option value="insurance">Insurance</option>
                  </select>
                  <button
                    type="submit"
                    disabled={formLoading}
                    className="px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {formLoading ? 'Recording...' : 'Record'}
                  </button>
                </form>
              </div>
            )}

            {/* Ledger Entries Table */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              {loading ? (
                <div className="p-6 space-y-4">
                  {[1, 2, 3, 4, 5].map(i => (
                    <div key={i} className="flex items-center gap-4 animate-pulse">
                      <div className="w-20 h-4 bg-gray-200 rounded" />
                      <div className="flex-1 h-4 bg-gray-200 rounded" />
                      <div className="w-16 h-5 bg-gray-100 rounded-full" />
                      <div className="w-20 h-4 bg-gray-200 rounded" />
                      <div className="w-20 h-4 bg-gray-100 rounded" />
                    </div>
                  ))}
                </div>
              ) : entries.length === 0 ? (
                <div className="py-12 text-center text-gray-400 text-sm">
                  No ledger entries for this patient
                </div>
              ) : (
                <>
                  <div className="hidden sm:grid grid-cols-[100px_1fr_100px_100px_110px] gap-4 px-6 py-3 bg-gray-50 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
                    <span>Date</span>
                    <span>Description</span>
                    <span>Type</span>
                    <span className="text-right">Amount</span>
                    <span className="text-right">Balance</span>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {entries.map(entry => (
                      <div key={entry.id} className="grid grid-cols-1 sm:grid-cols-[100px_1fr_100px_100px_110px] gap-2 sm:gap-4 px-6 py-3.5 items-center hover:bg-gray-50/50 transition-colors">
                        <span className="text-sm text-gray-600">{formatDate(entry.date)}</span>
                        <span className="text-sm text-gray-900">{entry.description}</span>
                        <span>
                          <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${TYPE_BADGES[entry.type]?.color || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                            {TYPE_BADGES[entry.type]?.label || entry.type}
                          </span>
                        </span>
                        <span className={`text-sm text-right font-medium ${entry.type === 'charge' ? 'text-red-600' : 'text-emerald-600'}`}>
                          {entry.type === 'charge' ? '' : '-'}{formatCurrency(Math.abs(entry.amount))}
                        </span>
                        <span className="text-sm text-right text-gray-700 font-medium">{formatCurrency(entry.running_balance)}</span>
                      </div>
                    ))}
                  </div>
                    </>
  )}
            </div>
              </>
  )}
          </>
  )
}
