import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
  FileText, Search, ChevronRight, ChevronDown, Loader2, Send,
  Shield, Receipt, CreditCard, UserCircle,
} from 'lucide-react'
import { api } from '../lib/api'

interface RosterEntry {
  patient_id: string
  patient_name: string
  claim_count: number
  status_counts: Record<string, number>
  total_billed: number
  total_paid: number
  total_outstanding: number
  latest_service_date: string | null
}

interface Claim {
  id: string
  patient_name: string
  payer_id: string
  claim_number: string | null
  total_billed: number
  total_paid: number | null
  patient_responsibility: number | null
  status: string
  service_date: string
  denial_reason: string | null
}

const STATUS_BADGES: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600', submitted: 'bg-blue-100 text-blue-700',
  accepted: 'bg-emerald-100 text-emerald-700', paid: 'bg-green-100 text-green-700',
  denied: 'bg-red-100 text-red-600', appealed: 'bg-amber-100 text-amber-700',
}

function money(n: number | null | undefined): string {
  if (n == null) return '—'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

export default function Claims() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [roster, setRoster] = useState<RosterEntry[]>([])
  const [meta, setMeta] = useState<{ count: number; total_claims: number }>({ count: 0, total_claims: 0 })
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [claimsByPatient, setClaimsByPatient] = useState<Record<string, Claim[]>>({})
  const [loadingClaims, setLoadingClaims] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState<string | null>(null)

  const loadRoster = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.getClaimsRoster()
      if (res.ok) {
        const data = await res.json()
        setRoster(data.patients || [])
        setMeta({ count: data.count || 0, total_claims: data.total_claims || 0 })
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
    if (!claimsByPatient[patientId]) {
      setLoadingClaims(patientId)
      try {
        const res = await api.getClaimsByPatient(patientId)
        if (res.ok) {
          const data = await res.json()
          setClaimsByPatient(prev => ({ ...prev, [patientId]: data.claims || [] }))
        }
      } catch { /* handled */ }
      setLoadingClaims(null)
    }
  }

  async function submitClaim(patientId: string, claimId: string) {
    setSubmitting(claimId)
    try {
      const res = await api.submitClaim(claimId)
      if (res.ok) {
        const r = await api.getClaimsByPatient(patientId)
        if (r.ok) { const d = await r.json(); setClaimsByPatient(prev => ({ ...prev, [patientId]: d.claims || [] })) }
        loadRoster()
      }
    } catch { /* handled */ }
    setSubmitting(null)
  }

  const filtered = roster.filter(r => {
    if (!filter.trim()) return true
    return r.patient_name.toLowerCase().includes(filter.toLowerCase())
  })

  return (
    <div data-testid="claims-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Claims</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {meta.total_claims} claims across {meta.count} patients
          </p>
        </div>
      </div>

      <div className="relative mb-4 max-w-md">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          data-testid="claims-filter"
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
          <FileText size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-sm text-gray-400">No claims match “{filter}”.</p>
        </div>
      ) : (
        <div className="space-y-2" data-testid="claims-roster">
          {filtered.map(r => {
            const isOpen = expandedId === r.patient_id
            return (
              <div key={r.patient_id} className="bg-white rounded-xl border border-gray-200/80 shadow-sm overflow-hidden">
                <button
                  data-testid={`claims-row-${r.patient_id}`}
                  onClick={() => expand(r.patient_id)}
                  className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
                >
                  {isOpen ? <ChevronDown size={16} className="text-gray-400 shrink-0" /> : <ChevronRight size={16} className="text-gray-400 shrink-0" />}
                  <div className="flex-1 min-w-0">
                    <span className="font-medium text-gray-900">{r.patient_name}</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {Object.entries(r.status_counts).map(([st, ct]) => (
                        <span key={st} className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_BADGES[st] || 'bg-gray-100 text-gray-600'}`}>
                          {ct} {st}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="hidden sm:block text-right shrink-0">
                    <p className="text-xs text-gray-400">Billed</p>
                    <p className="text-sm font-medium text-gray-900">{money(r.total_billed)}</p>
                  </div>
                  <div className="hidden md:block text-right shrink-0 w-24">
                    <p className="text-xs text-gray-400">Outstanding</p>
                    <p className={`text-sm font-medium ${r.total_outstanding > 0 ? 'text-amber-600' : 'text-gray-900'}`}>{money(r.total_outstanding)}</p>
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-gray-100 p-4 bg-gray-50/50" data-testid={`claims-panel-${r.patient_id}`}>
                    <div className="flex flex-wrap gap-2 mb-4">
                      <QuickLink icon={UserCircle} label="Patient Record" onClick={() => navigate(`/patients/${r.patient_id}`)} />
                      <QuickLink icon={Shield} label="Insurance" onClick={() => navigate(`/insurance?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={Receipt} label="Ledger" onClick={() => navigate(`/ledger?patient_id=${r.patient_id}`)} />
                      <QuickLink icon={CreditCard} label="Payments" onClick={() => navigate(`/payments?patient_id=${r.patient_id}`)} />
                    </div>

                    {loadingClaims === r.patient_id ? (
                      <div className="flex items-center gap-2 text-sm text-gray-400 py-4"><Loader2 size={14} className="animate-spin" /> Loading claims…</div>
                    ) : (claimsByPatient[r.patient_id] || []).length === 0 ? (
                      <p className="text-sm text-gray-400 py-2">No claims found.</p>
                    ) : (
                      <div className="space-y-2">
                        {claimsByPatient[r.patient_id].map(claim => (
                          <div key={claim.id} className="bg-white rounded-xl border border-gray-200/80 p-3.5">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-gray-900 text-sm">{claim.claim_number || 'Draft claim'}</span>
                                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${STATUS_BADGES[claim.status] || 'bg-gray-100 text-gray-600'}`}>{claim.status}</span>
                                </div>
                                <p className="text-xs text-gray-500 mt-0.5">
                                  Service {claim.service_date} · Billed {money(claim.total_billed)}
                                  {claim.total_paid != null ? ` · Paid ${money(claim.total_paid)}` : ''}
                                  {claim.patient_responsibility != null ? ` · Patient ${money(claim.patient_responsibility)}` : ''}
                                </p>
                                {claim.denial_reason && <p className="text-xs text-red-600 mt-0.5">Denial: {claim.denial_reason}</p>}
                              </div>
                              {claim.status === 'draft' && (
                                <button
                                  data-testid={`submit-claim-${claim.id}`}
                                  onClick={() => submitClaim(r.patient_id, claim.id)}
                                  disabled={submitting === claim.id}
                                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-teal-50 text-teal-700 border border-teal-200 rounded-lg hover:bg-teal-100 transition-colors disabled:opacity-50 shrink-0"
                                >
                                  {submitting === claim.id ? <><Loader2 size={12} className="animate-spin" /> Submitting…</> : <><Send size={12} /> Submit</>}
                                </button>
                              )}
                            </div>
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
