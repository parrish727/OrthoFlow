import { useState, useEffect, useCallback } from 'react'
import { X, Loader2, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'

export type FinanceSection = 'ledger' | 'insurance' | 'claims' | 'payments'

const TITLES: Record<FinanceSection, string> = {
  ledger: 'Ledger', insurance: 'Insurance', claims: 'Claims', payments: 'Payments',
}
// Full-page routes kept as well — modal offers an "Open full page" escape hatch.
const ROUTES: Record<FinanceSection, string> = {
  ledger: '/ledger', insurance: '/insurance', claims: '/claims', payments: '/payments',
}

function money(n: number | null | undefined) {
  if (n == null) return '$0.00'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

interface LedgerEntry { id: string; entry_type: string; description: string; amount: number; posted_date: string | null; payment_method?: string | null }
interface InsurancePlan { id: string; payer_name?: string; plan_name?: string; plan_type?: string; ortho_lifetime_max?: number | null; ortho_lifetime_used?: number | null; remaining_benefit?: number | null; ortho_coverage_pct?: number | null }
interface ClaimRow { id: string; status?: string; total_billed?: number; claim_number?: string; service_date?: string }

// In-place modal for a patient's finance sections. Opens over the patient profile — the
// Frontdesk/Finance user sees the data right there without jumping to the section page.
export default function PatientFinanceModal({
  patientId, section, onClose,
}: { patientId: string; section: FinanceSection; onClose: () => void }) {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [entries, setEntries] = useState<LedgerEntry[]>([])
  const [balance, setBalance] = useState<number | null>(null)
  const [plans, setPlans] = useState<InsurancePlan[]>([])
  const [claims, setClaims] = useState<ClaimRow[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      if (section === 'ledger' || section === 'payments') {
        const [ledgerRes, sumRes] = await Promise.all([api.getLedger(patientId), api.getLedgerSummary(patientId)])
        if (ledgerRes.ok) {
          const d = await ledgerRes.json()
          setEntries(d.entries || [])
        }
        if (sumRes.ok) setBalance((await sumRes.json()).balance)
      } else if (section === 'insurance') {
        const res = await api.getInsurancePlans(patientId)
        if (res.ok) setPlans((await res.json()).insurance_plans || [])
      } else if (section === 'claims') {
        const res = await api.getClaimsByPatient(patientId)
        if (res.ok) {
          const d = await res.json()
          setClaims(Array.isArray(d) ? d : d.claims || [])
        }
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [patientId, section])

  useEffect(() => { load() }, [load])

  const payments = entries.filter(e => e.entry_type === 'payment')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" data-testid="finance-modal">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-gray-100">
          <h3 className="text-sm font-semibold text-gray-900" data-testid="finance-modal-title">{TITLES[section]}</h3>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(`${ROUTES[section]}?patient_id=${patientId}`)}
              className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700"
            >
              <ExternalLink size={12} /> Open full page
            </button>
            <button onClick={onClose} aria-label="Close" className="p-1 hover:bg-gray-100 rounded-lg"><X size={18} className="text-gray-500" /></button>
          </div>
        </div>

        <div className="overflow-y-auto p-5">
          {loading ? (
            <div className="py-10 text-center"><Loader2 size={20} className="animate-spin text-gray-400 mx-auto" /></div>
          ) : section === 'ledger' ? (
            <>
              <div className="mb-3 flex items-baseline gap-2">
                <span className="text-xs text-gray-500">Balance</span>
                <span className={`text-lg font-bold ${(balance || 0) > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{money(balance)}</span>
              </div>
              {entries.length === 0 ? <p className="text-sm text-gray-400 text-center py-6">No ledger entries</p> : (
                <div className="divide-y divide-gray-50">
                  {entries.map(e => (
                    <div key={e.id} className="py-2.5 flex items-center justify-between gap-3" data-testid="modal-ledger-entry">
                      <div className="min-w-0">
                        <p className="text-sm text-gray-800 truncate">{e.description}</p>
                        <p className="text-[10px] text-gray-400">{e.posted_date} · {e.entry_type}</p>
                      </div>
                      <span className={`text-sm font-medium ${e.amount < 0 ? 'text-emerald-600' : 'text-gray-800'}`}>{money(e.amount)}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : section === 'payments' ? (
            payments.length === 0 ? <p className="text-sm text-gray-400 text-center py-6">No payments recorded</p> : (
              <div className="divide-y divide-gray-50">
                {payments.map(e => (
                  <div key={e.id} className="py-2.5 flex items-center justify-between gap-3" data-testid="modal-payment-entry">
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800 truncate">{e.description}</p>
                      <p className="text-[10px] text-gray-400">{e.posted_date}{e.payment_method ? ` · ${e.payment_method}` : ''}</p>
                    </div>
                    <span className="text-sm font-medium text-emerald-600">{money(Math.abs(e.amount))}</span>
                  </div>
                ))}
              </div>
            )
          ) : section === 'insurance' ? (
            plans.length === 0 ? <p className="text-sm text-gray-400 text-center py-6">No insurance on file</p> : (
              <div className="space-y-3">
                {plans.map(p => {
                  const remaining = p.remaining_benefit ?? ((p.ortho_lifetime_max ?? 0) - (p.ortho_lifetime_used ?? 0))
                  return (
                    <div key={p.id} className="border border-gray-200 rounded-xl p-3" data-testid="modal-insurance-plan">
                      <p className="text-sm font-semibold text-gray-900">{p.payer_name}</p>
                      <p className="text-xs text-gray-500">{p.plan_name} · {p.plan_type}</p>
                      <div className="grid grid-cols-3 gap-2 mt-2 text-center">
                        <div><p className="text-[10px] text-gray-400">Lifetime Max</p><p className="text-sm font-medium">{money(p.ortho_lifetime_max)}</p></div>
                        <div><p className="text-[10px] text-gray-400">Used</p><p className="text-sm font-medium">{money(p.ortho_lifetime_used)}</p></div>
                        <div><p className="text-[10px] text-gray-400">Remaining</p><p className="text-sm font-medium text-emerald-600">{money(remaining)}</p></div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )
          ) : (
            claims.length === 0 ? <p className="text-sm text-gray-400 text-center py-6">No claims</p> : (
              <div className="divide-y divide-gray-50">
                {claims.map(c => (
                  <div key={c.id} className="py-2.5 flex items-center justify-between gap-3" data-testid="modal-claim-row">
                    <div className="min-w-0">
                      <p className="text-sm text-gray-800">{c.claim_number || `Claim ${c.id.slice(0, 8)}`}</p>
                      <p className="text-[10px] text-gray-400">{c.service_date || ''}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-sm font-medium text-gray-800">{money(c.total_billed)}</span>
                      {c.status && <p className="text-[10px] text-gray-500 capitalize">{c.status}</p>}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </div>
      </div>
    </div>
  )
}
