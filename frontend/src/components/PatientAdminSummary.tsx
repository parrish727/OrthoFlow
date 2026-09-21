import { useState, useEffect, useCallback } from 'react'
import { DollarSign, Shield, FileText, Loader2, ArrowRight } from 'lucide-react'
import { api } from '../lib/api'
import type { FinanceSection } from './PatientFinanceModal'

interface LedgerSummary { total_charges: number; total_payments: number; balance: number }
interface InsurancePlan { id: string; payer_name?: string; plan_type?: string; subscriber_id?: string; remaining_benefit?: number | null }
interface ClaimRow { id: string; status?: string; total_billed?: number }

function fmt(n: number | null | undefined) {
  if (n == null) return '$0.00'
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

// Self-contained Frontdesk/Finance summary for a patient — lives in the Administrative tab.
// Shows balance, insurance, and claims INLINE so the front desk sees everything for that
// patient without leaving the tab. Each card still deep-links to the full page for that
// exact patient (patient_id carried through) for drill-down.
export default function PatientAdminSummary({ patientId, onOpenSection }: { patientId: string; onOpenSection: (s: FinanceSection) => void }) {
  const [ledger, setLedger] = useState<LedgerSummary | null>(null)
  const [plans, setPlans] = useState<InsurancePlan[]>([])
  const [claims, setClaims] = useState<ClaimRow[]>([])
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [ledgerRes, insRes, claimsRes] = await Promise.all([
        api.getLedgerSummary(patientId),
        api.getInsurancePlans(patientId),
        api.getClaimsByPatient(patientId),
      ])
      if (ledgerRes.ok) setLedger(await ledgerRes.json())
      if (insRes.ok) {
        const d = await insRes.json()
        setPlans(Array.isArray(d) ? d : d.plans || d.subscribers || [])
      }
      if (claimsRes.ok) {
        const d = await claimsRes.json()
        setClaims(Array.isArray(d) ? d : d.claims || [])
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [patientId])

  useEffect(() => { load() }, [load])

  const openClaims = claims.filter(c => c.status && !['paid', 'closed', 'denied'].includes(c.status)).length

  if (loading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-8 text-center" data-testid="patient-admin-summary">
        <Loader2 size={18} className="animate-spin text-gray-400 mx-auto" />
      </div>
    )
  }

  return (
    <div className="space-y-4" data-testid="patient-admin-summary">
      {/* Balance */}
      <button
        data-testid="admin-balance-card"
        onClick={() => onOpenSection('ledger')}
        className="w-full text-left bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 hover:border-teal-300 transition-colors group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><DollarSign size={15} className="text-teal-600" /><h3 className="text-sm font-semibold text-gray-800">Account Balance</h3></div>
          <ArrowRight size={15} className="text-gray-300 group-hover:text-teal-600 transition-colors" />
        </div>
        <p className={`text-2xl font-bold ${(ledger?.balance || 0) > 0 ? 'text-amber-700' : 'text-emerald-700'}`}>{fmt(ledger?.balance)}</p>
        <div className="flex gap-4 mt-2 text-xs text-gray-500">
          <span>Charges {fmt(ledger?.total_charges)}</span>
          <span>Paid {fmt(Math.abs(ledger?.total_payments || 0))}</span>
        </div>
      </button>

      {/* Insurance */}
      <button
        data-testid="admin-insurance-card"
        onClick={() => onOpenSection('insurance')}
        className="w-full text-left bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 hover:border-teal-300 transition-colors group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><Shield size={15} className="text-teal-600" /><h3 className="text-sm font-semibold text-gray-800">Insurance</h3></div>
          <ArrowRight size={15} className="text-gray-300 group-hover:text-teal-600 transition-colors" />
        </div>
        {plans.length === 0 ? (
          <p className="text-sm text-gray-400">No insurance on file</p>
        ) : (
          <div className="space-y-1.5">
            {plans.slice(0, 2).map(p => (
              <div key={p.id} className="text-sm">
                <span className="font-medium text-gray-800">{p.payer_name || 'Plan'}</span>
                {p.plan_type && <span className="text-gray-400 ml-1">· {p.plan_type}</span>}
                {p.remaining_benefit != null && <span className="text-gray-500 ml-1">· {fmt(p.remaining_benefit)} remaining</span>}
              </div>
            ))}
          </div>
        )}
      </button>

      {/* Claims */}
      <button
        data-testid="admin-claims-card"
        onClick={() => onOpenSection('claims')}
        className="w-full text-left bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 hover:border-teal-300 transition-colors group"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2"><FileText size={15} className="text-teal-600" /><h3 className="text-sm font-semibold text-gray-800">Claims</h3></div>
          <ArrowRight size={15} className="text-gray-300 group-hover:text-teal-600 transition-colors" />
        </div>
        <p className="text-sm text-gray-700">
          <span className="font-semibold">{claims.length}</span> total
          {openClaims > 0 && <span className="text-amber-700 ml-2">· {openClaims} open</span>}
        </p>
      </button>
    </div>
  )
}
