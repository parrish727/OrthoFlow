import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  CreditCard, Search, ChevronRight, ChevronDown, Loader2,
  Shield, FileText, Receipt, UserCircle,
} from 'lucide-react'
import { api } from '../lib/api'

interface RosterEntry {
  patient_id: string
  first_name: string
  last_name: string
  total_paid: number
  payment_count: number
  last_payment_date: string | null
}

interface LedgerEntry {
  id: string
  entry_type: string
  description: string
  amount: number
  posted_date: string | null
  payment_method: string | null
  reference_number: string | null
}

function money(n: number | null | undefined): string {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

export default function Payments() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [roster, setRoster] = useState<RosterEntry[]>([])
  const [meta, setMeta] = useState<{ count: number }>({ count: 0 })
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [paymentsByPatient, setPaymentsByPatient] = useState<Record<string, LedgerEntry[]>>({})
  const [loadingPayments, setLoadingPayments] = useState<string | null>(null)

  const loadRoster = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.getPaymentsRoster()
      if (res.ok) {
        const data = await res.json()
        setRoster(data.patients || [])
        setMeta({ count: data.count || 0 })
      }
    } catch { /* handled */ }
    setLoading(false)
  }, [])

  useEffect(() => { loadRoster() }, [loadRoster])

  useEffect(() => {
    const pid = searchParams.get('patient_id')
    if (pid && roster.length > 0) expand(pid)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roster])

  async function expand(patientId: string) {
    if (expandedId === patientId) { setExpandedId(null); return }
    setExpandedId(patientId)
    if (!paymentsByPatient[patientId]) {
      setLoadingPayments(patientId)
      try {
        const res = await api.getLedger(patientId)
        if (res.ok) {
          const data = await res.json()
          const payments = (data.entries || []).filter((e: LedgerEntry) => e.entry_type === 'payment')
          setPaymentsByPatient(prev => ({ ...prev, [patientId]: payments }))
        }
      } catch { /* handled */ }
      setLoadingPayments(null)
    }
  }

  const filtered = roster.filter(r =>
    !filter.trim() || `${r.first_name} ${r.last_name}`.toLowerCase().includes(filter.toLowerCase()))

  const totalCollected = roster.reduce((a, r) => a + r.total_paid, 0)

  return (
    <div data-testid="payments-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Payments</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {money(totalCollected)} collected across {meta.count} patients
          </p>
        </div>
      </div>

      <div className="relative mb-4 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          data-testid="payments-filter"
          type="text"
          placeholder="Filter by patient…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="w-full pl-9 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300"
        />
      </div>

      {loading ? (
        <div className="space-y-2">{[1, 2, 3, 4, 5].map(i => <div key={i} className="h-16 bg-white rounded-xl border border-gray-200/70 animate-pulse" />)}</div>
      ) : filtered.length === 0 ? (
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm py-16 text-center">
          <CreditCard size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No payments match “{filter}”.</p>
        </div>
      ) : (
        <div className="space-y-2" data-testid="payments-roster">
          {filtered.map(r => {
            const isOpen = expandedId === r.patient_id
            return (
              <div key={r.patient_id} className="bg-white rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
                <button
                  data-testid={`payments-row-${r.patient_id}`}
                  onClick={() => expand(r.patient_id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  {isOpen ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-gray-900">{r.last_name}, {r.first_name}</span>
                    <p className="text-xs text-gray-500">
                      {r.payment_count} payment{r.payment_count !== 1 ? 's' : ''}
                      {r.last_payment_date ? ` · last ${r.last_payment_date}` : ''}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-gray-400">Total paid</p>
                    <p className="text-sm font-medium text-emerald-600">{money(r.total_paid)}</p>
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50/50" data-testid={`payments-panel-${r.patient_id}`}>
                    <div className="flex flex-wrap gap-2 mb-4">
                      <QuickLink icon={UserCircle} label="Patient Record" onClick={() => navigate(`/patients/${r.patient_id}`)} />
                      <QuickLink icon={Shield} label="Insurance" onClick={() => navigate(`/insurance?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={FileText} label="Claims" onClick={() => navigate(`/claims?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={Receipt} label="Ledger" onClick={() => navigate(`/ledger?patient_id=${r.patient_id}`)} />
                    </div>

                    {loadingPayments === r.patient_id ? (
                      <div className="flex items-center gap-2 text-sm text-gray-400 py-4"><Loader2 size={14} className="animate-spin" /> Loading payments…</div>
                    ) : (paymentsByPatient[r.patient_id] || []).length === 0 ? (
                      <p className="text-sm text-gray-400 py-2">No payments recorded.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {paymentsByPatient[r.patient_id].map(pmt => (
                          <div key={pmt.id} className="flex items-center justify-between bg-white rounded-lg border border-gray-200/70 px-3 py-2">
                            <div className="min-w-0">
                              <p className="text-sm text-gray-800 truncate">{pmt.description}</p>
                              <p className="text-xs text-gray-400">
                                {pmt.posted_date || '—'}{pmt.payment_method ? ` · ${pmt.payment_method}` : ''}{pmt.reference_number ? ` · ${pmt.reference_number}` : ''}
                              </p>
                            </div>
                            <span className="text-sm font-medium text-emerald-600 shrink-0">{money(Math.abs(pmt.amount))}</span>
                          </div>
                        ))}
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
