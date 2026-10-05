import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { DollarSign, TrendingUp, Users, ChevronDown, Shield, FileText, CreditCard, UserCircle, Search, StickyNote, Loader2, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'
import AIAssist from '../components/AIAssist'
import PracticeImpact from '../components/PracticeImpact'

interface PatientBalance {
  id: string
  first_name: string
  last_name: string
  balance: number
  total_charges: number
  total_payments: number
  aging_bucket: string
  days_overdue: number | null
  delinquent_90_plus: boolean
  ar_note: string | null
  ar_note_updated_at: string | null
}

interface LedgerEntry {
  id: string
  entry_type: string
  description: string
  amount: number
  running_balance: number | null
  posted_date: string | null
  payment_method: string | null
  is_auto_pay?: boolean
  auto_pay_status?: 'resolved' | 'failed' | null
}

// Aging bucket → badge styling. 90+ buckets are visually escalated (this is the long-tail
// delinquency TOPS dumps to collections; OrthoFlow keeps tracking + noting it).
const BUCKET_STYLE: Record<string, string> = {
  current: 'bg-gray-100 text-gray-500',
  '31-60': 'bg-yellow-100 text-yellow-700',
  '61-90': 'bg-amber-100 text-amber-700',
  '90-120': 'bg-orange-100 text-orange-700',
  '120+': 'bg-red-100 text-red-700',
}
const BUCKET_LABEL: Record<string, string> = {
  current: 'Current', '31-60': '31–60d', '61-90': '61–90d', '90-120': '90–120d', '120+': '120+d',
}

export default function Ledger() {
  const navigate = useNavigate()
  const [patients, setPatients] = useState<PatientBalance[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [entriesLoading, setEntriesLoading] = useState(false)
  const [searchParams] = useSearchParams()
  const [search, setSearch] = useState('')
  const [only90, setOnly90] = useState(false)

  useEffect(() => { loadAllBalances() }, [])

  useEffect(() => {
    const patientIdFromUrl = searchParams.get('patient_id')
    if (patientIdFromUrl && !expandedId) {
      setExpandedId(patientIdFromUrl)
      loadEntries(patientIdFromUrl)
    }
  }, [searchParams])

  async function loadAllBalances() {
    setLoading(true)
    try {
      const res = await api.getLedgerRoster()
      if (res.ok) {
        const data = await res.json()
        setPatients((data.patients || []).map((p: PatientBalance & { patient_id?: string }) => ({
          id: p.patient_id || p.id, first_name: p.first_name, last_name: p.last_name,
          balance: p.balance, total_charges: p.total_charges, total_payments: p.total_payments,
          aging_bucket: p.aging_bucket, days_overdue: p.days_overdue, delinquent_90_plus: p.delinquent_90_plus,
          ar_note: p.ar_note, ar_note_updated_at: p.ar_note_updated_at,
        })))
      }
    } catch {}
    setLoading(false)
  }

  async function loadEntries(patientId: string) {
    setEntriesLoading(true)
    try {
      const res = await api.getLedger(patientId)
      if (res.ok) {
        const data = await res.json()
        setEntries(data.entries || [])
      }
    } catch {}
    setEntriesLoading(false)
  }

  async function toggleExpand(patientId: string) {
    if (expandedId === patientId) { setExpandedId(null); return }
    setExpandedId(patientId)
    await loadEntries(patientId)
  }

  function onNoteSaved(patientId: string, note: string | null, updatedAt: string | null) {
    setPatients(prev => prev.map(p => p.id === patientId ? { ...p, ar_note: note, ar_note_updated_at: updatedAt } : p))
  }

  const totals = patients.reduce((acc, p) => ({ charges: acc.charges + p.total_charges, payments: acc.payments + Math.abs(p.total_payments), balance: acc.balance + p.balance }), { charges: 0, payments: 0, balance: 0 })
  const count90 = patients.filter(p => p.delinquent_90_plus).length

  // Client-side filter (roster is a single call): search by name + optional 90+ delinquency filter.
  const q = search.trim().toLowerCase()
  const visible = patients.filter(p => {
    if (only90 && !p.delinquent_90_plus) return false
    if (!q) return true
    return `${p.first_name} ${p.last_name}`.toLowerCase().includes(q) || `${p.last_name} ${p.first_name}`.toLowerCase().includes(q)
  })

  function fmt(n: number) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n) }

  return (
    <div data-testid="ledger-page">
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Ledger</h2>
        <p className="text-sm text-gray-500 mt-0.5">Patient balances, aging, and transaction history</p>
      </div>

      <div className="mb-6"><PracticeImpact /></div>
      <div className="mb-6"><AIAssist /></div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
          <div className="flex items-center gap-2 mb-1"><DollarSign size={16} className="text-gray-400" /><span className="text-xs text-gray-500">Total Charges</span></div>
          <p className="text-xl font-bold text-gray-900">{fmt(totals.charges)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
          <div className="flex items-center gap-2 mb-1"><TrendingUp size={16} className="text-emerald-500" /><span className="text-xs text-gray-500">Collected</span></div>
          <p className="text-xl font-bold text-emerald-700">{fmt(totals.payments)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
          <div className="flex items-center gap-2 mb-1"><DollarSign size={16} className="text-amber-500" /><span className="text-xs text-gray-500">Outstanding</span></div>
          <p className="text-xl font-bold text-amber-700">{fmt(totals.balance)}</p>
        </div>
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
          <div className="flex items-center gap-2 mb-1"><AlertTriangle size={16} className="text-red-500" /><span className="text-xs text-gray-500">90+ Days Delinquent</span></div>
          <p className="text-xl font-bold text-red-700">{count90}</p>
        </div>
      </div>

      {/* Search + 90+ filter */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="relative flex-1 min-w-[220px] max-w-md">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            data-testid="ledger-search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search patient by name…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500/40"
          />
        </div>
        <button
          data-testid="ledger-filter-90plus"
          onClick={() => setOnly90(v => !v)}
          className={`flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-xl border transition-colors ${only90 ? 'bg-red-600 text-white border-red-600' : 'bg-white text-gray-700 border-gray-200 hover:bg-red-50 hover:text-red-700 hover:border-red-200'}`}
        >
          <AlertTriangle size={14} /> 90+ Days {only90 ? '✓' : `(${count90})`}
        </button>
      </div>

      {/* Patient Balance Table */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading balances...</div>
        ) : visible.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">{patients.length === 0 ? 'No patient balances found' : 'No patients match your filters'}</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase">Patient</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase">Aging</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Charges</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Paid</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50" data-testid="ledger-roster">
              {visible.map(p => (
                <PatientRow key={p.id} patient={p} expanded={expandedId === p.id} entries={expandedId === p.id ? entries : []} entriesLoading={entriesLoading && expandedId === p.id} onToggle={() => toggleExpand(p.id)} fmt={fmt} navigate={navigate} onNoteSaved={onNoteSaved} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function PatientRow({ patient, expanded, entries, entriesLoading, onToggle, fmt, navigate, onNoteSaved }: { patient: PatientBalance; expanded: boolean; entries: LedgerEntry[]; entriesLoading: boolean; onToggle: () => void; fmt: (n: number) => string; navigate: (to: string) => void; onNoteSaved: (id: string, note: string | null, at: string | null) => void }) {
  const [noteDraft, setNoteDraft] = useState(patient.ar_note || '')
  const [savingNote, setSavingNote] = useState(false)
  const [noteMsg, setNoteMsg] = useState('')

  useEffect(() => { setNoteDraft(patient.ar_note || '') }, [patient.ar_note])

  async function saveNote() {
    setSavingNote(true)
    setNoteMsg('')
    try {
      const res = await api.updateArNote(patient.id, noteDraft)
      if (res.ok) {
        const data = await res.json()
        onNoteSaved(patient.id, data.ar_note, data.ar_note_updated_at)
        setNoteMsg('Saved ✓')
      } else { setNoteMsg('Save failed') }
    } catch { setNoteMsg('Save failed') }
    setSavingNote(false)
  }

  return (
    <>
      <tr data-testid={`ledger-row-${patient.id}`} onClick={onToggle} className="cursor-pointer hover:bg-gray-50 transition-colors">
        <td className="px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-teal-100 to-teal-200 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-teal-700">{patient.first_name[0]}{patient.last_name[0]}</span>
            </div>
            <span className="text-sm font-medium text-gray-900">{patient.last_name}, {patient.first_name}</span>
            {patient.ar_note && <StickyNote size={13} className="text-amber-500" data-testid={`ar-note-indicator-${patient.id}`} />}
            <ChevronDown size={14} className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </div>
        </td>
        <td className="px-6 py-3">
          {patient.balance > 0 ? (
            <span data-testid={`aging-badge-${patient.id}`} className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${BUCKET_STYLE[patient.aging_bucket] || 'bg-gray-100 text-gray-500'}`}>
              {BUCKET_LABEL[patient.aging_bucket] || patient.aging_bucket}{patient.days_overdue != null ? ` · ${patient.days_overdue}d` : ''}
            </span>
          ) : <span className="text-[10px] text-gray-300">—</span>}
        </td>
        <td className="px-6 py-3 text-right text-sm text-gray-700">{fmt(patient.total_charges)}</td>
        <td className="px-6 py-3 text-right text-sm text-emerald-600">{fmt(Math.abs(patient.total_payments))}</td>
        <td className="px-6 py-3 text-right">
          <span className={`text-sm font-semibold ${patient.balance > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{fmt(patient.balance)}</span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={5} className="px-6 py-3 bg-gray-50/50">
            <div className="flex flex-wrap gap-2 mb-3" onClick={e => e.stopPropagation()}>
              <button data-testid="quicklink-patient-record" onClick={() => navigate(`/patients/${patient.id}`)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-700 border border-gray-200 rounded-full hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"><UserCircle size={13} /> Patient Record</button>
              <button data-testid="quicklink-insurance" onClick={() => navigate(`/insurance?patient_id=${patient.id}`)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-700 border border-gray-200 rounded-full hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"><Shield size={13} /> Insurance</button>
              <button data-testid="quicklink-claims" onClick={() => navigate(`/claims?patient_id=${patient.id}`)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-700 border border-gray-200 rounded-full hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"><FileText size={13} /> Claims</button>
              <button data-testid="quicklink-payments" onClick={() => navigate(`/payments?patient_id=${patient.id}`)} className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white text-gray-700 border border-gray-200 rounded-full hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"><CreditCard size={13} /> Payments</button>
            </div>

            {/* AR / collections note — single place for financial-coordinator contact notes */}
            <div className="mb-3 bg-white rounded-xl border border-gray-200 p-3" onClick={e => e.stopPropagation()} data-testid={`ar-note-editor-${patient.id}`}>
              <div className="flex items-center gap-1.5 mb-2">
                <StickyNote size={13} className="text-amber-500" />
                <span className="text-xs font-semibold text-gray-700">AR / Collections Note</span>
                {patient.ar_note_updated_at && <span className="text-[10px] text-gray-400 ml-auto">updated {new Date(patient.ar_note_updated_at).toLocaleDateString()}</span>}
              </div>
              <textarea
                data-testid={`ar-note-input-${patient.id}`}
                value={noteDraft}
                onChange={e => setNoteDraft(e.target.value)}
                rows={2}
                placeholder="e.g. Spoke with mom — will pay Friday 10/10"
                className="w-full text-sm border border-gray-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-teal-500/40 resize-none"
              />
              <div className="flex items-center gap-2 mt-2">
                <button
                  data-testid={`ar-note-save-${patient.id}`}
                  onClick={saveNote}
                  disabled={savingNote || noteDraft === (patient.ar_note || '')}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50 rounded-lg transition-colors"
                >
                  {savingNote ? <Loader2 size={12} className="animate-spin" /> : <StickyNote size={12} />} Save Note
                </button>
                {noteMsg && <span className="text-[11px] text-gray-500">{noteMsg}</span>}
              </div>
            </div>

            {entriesLoading ? (
              <p className="text-xs text-gray-400 py-2">Loading transactions...</p>
            ) : entries.length === 0 ? (
              <p className="text-xs text-gray-400 py-2">No transactions</p>
            ) : (
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-gray-400 uppercase">
                    <th className="py-1 text-left">Date</th>
                    <th className="py-1 text-left">Description</th>
                    <th className="py-1 text-left">Type</th>
                    <th className="py-1 text-right">Amount</th>
                    <th className="py-1 text-right">Balance</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {entries.map(e => (
                    <tr key={e.id} data-testid={`ledger-entry-${e.id}`} className={
                      e.is_auto_pay && e.auto_pay_status === 'failed' ? 'bg-red-50'
                      : e.is_auto_pay && e.auto_pay_status === 'resolved' ? 'bg-emerald-50/60'
                      : ''
                    }>
                      <td className="py-1.5 text-gray-500">{e.posted_date || '—'}</td>
                      <td className="py-1.5 text-gray-700">
                        <span className="inline-flex items-center gap-1.5">
                          {e.description}
                          {e.is_auto_pay && (
                            <span
                              data-testid={`autopay-${e.auto_pay_status}-${e.id}`}
                              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[9px] font-semibold border ${
                                e.auto_pay_status === 'failed'
                                  ? 'bg-red-100 text-red-700 border-red-300'
                                  : 'bg-emerald-100 text-emerald-700 border-emerald-300'
                              }`}
                              title={e.auto_pay_status === 'failed' ? 'Auto-pay failed — needs attention' : 'Auto-pay resolved'}
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${e.auto_pay_status === 'failed' ? 'bg-red-500' : 'bg-emerald-500'}`} />
                              {e.auto_pay_status === 'failed' ? 'AUTO-PAY FAILED' : 'AUTO-PAY'}
                            </span>
                          )}
                        </span>
                      </td>
                      <td className="py-1.5"><span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${e.entry_type === 'charge' ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>{e.entry_type}</span></td>
                      <td className={`py-1.5 text-right font-medium ${e.amount > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{fmt(e.amount)}</td>
                      <td className="py-1.5 text-right text-gray-500">{e.running_balance != null ? fmt(e.running_balance) : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </td>
        </tr>
      )}
    </>
  )
}
