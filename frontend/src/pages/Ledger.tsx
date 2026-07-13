import { useState, useEffect } from 'react'
import { DollarSign, TrendingUp, Users, ChevronDown } from 'lucide-react'
import { api } from '../lib/api'

interface PatientBalance {
  id: string
  first_name: string
  last_name: string
  balance: number
  total_charges: number
  total_payments: number
}

interface LedgerEntry {
  id: string
  entry_type: string
  description: string
  amount: number
  running_balance: number | null
  posted_date: string | null
  payment_method: string | null
}

export default function Ledger() {
  const [patients, setPatients] = useState<PatientBalance[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [entriesLoading, setEntriesLoading] = useState(false)

  useEffect(() => { loadAllBalances() }, [])

  async function loadAllBalances() {
    setLoading(true)
    try {
      const res = await api.getPatients({ search: '' })
      if (!res.ok) return
      const data = await res.json()
      const balances: PatientBalance[] = []
      for (const p of (data.patients || [])) {
        try {
          const sumRes = await api.getLedgerSummary(p.id)
          if (sumRes.ok) {
            const s = await sumRes.json()
            if (s.balance !== 0 || s.total_charges > 0) {
              balances.push({ id: p.id, first_name: p.first_name, last_name: p.last_name, balance: s.balance || 0, total_charges: s.total_charges || 0, total_payments: s.total_payments || 0 })
            }
          }
        } catch {}
      }
      balances.sort((a, b) => b.balance - a.balance)
      setPatients(balances)
    } catch {}
    setLoading(false)
  }

  async function toggleExpand(patientId: string) {
    if (expandedId === patientId) { setExpandedId(null); return }
    setExpandedId(patientId)
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

  const totals = patients.reduce((acc, p) => ({ charges: acc.charges + p.total_charges, payments: acc.payments + Math.abs(p.total_payments), balance: acc.balance + p.balance }), { charges: 0, payments: 0, balance: 0 })

  function fmt(n: number) { return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(n) }

  return (
    <>
      <div className="mb-6">
        <h2 className="text-2xl font-semibold text-gray-900">Ledger</h2>
        <p className="text-sm text-gray-500 mt-0.5">Patient balances and transaction history</p>
      </div>

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
          <div className="flex items-center gap-2 mb-1"><Users size={16} className="text-gray-400" /><span className="text-xs text-gray-500">Patients</span></div>
          <p className="text-xl font-bold text-gray-900">{patients.length}</p>
        </div>
      </div>

      {/* Patient Balance Table */}
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400 text-sm">Loading balances...</div>
        ) : patients.length === 0 ? (
          <div className="p-8 text-center text-gray-400 text-sm">No patient balances found</div>
        ) : (
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-100 text-left">
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase">Patient</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Charges</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Paid</th>
                <th className="px-6 py-3 text-xs font-medium text-gray-500 uppercase text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {patients.map(p => (
                <PatientRow key={p.id} patient={p} expanded={expandedId === p.id} entries={expandedId === p.id ? entries : []} entriesLoading={entriesLoading && expandedId === p.id} onToggle={() => toggleExpand(p.id)} fmt={fmt} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}

function PatientRow({ patient, expanded, entries, entriesLoading, onToggle, fmt }: { patient: PatientBalance; expanded: boolean; entries: LedgerEntry[]; entriesLoading: boolean; onToggle: () => void; fmt: (n: number) => string }) {
  return (
    <>
      <tr onClick={onToggle} className="cursor-pointer hover:bg-gray-50 transition-colors">
        <td className="px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-teal-100 to-teal-200 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-xs font-semibold text-teal-700">{patient.first_name[0]}{patient.last_name[0]}</span>
            </div>
            <span className="text-sm font-medium text-gray-900">{patient.last_name}, {patient.first_name}</span>
            <ChevronDown size={14} className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`} />
          </div>
        </td>
        <td className="px-6 py-3 text-right text-sm text-gray-700">{fmt(patient.total_charges)}</td>
        <td className="px-6 py-3 text-right text-sm text-emerald-600">{fmt(Math.abs(patient.total_payments))}</td>
        <td className="px-6 py-3 text-right">
          <span className={`text-sm font-semibold ${patient.balance > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{fmt(patient.balance)}</span>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={4} className="px-6 py-3 bg-gray-50/50">
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
                    <tr key={e.id}>
                      <td className="py-1.5 text-gray-500">{e.posted_date || '—'}</td>
                      <td className="py-1.5 text-gray-700">{e.description}</td>
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
