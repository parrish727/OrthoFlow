import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, PiggyBank, Timer, FileText, ChevronRight, X, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface ImpactItem {
  priority: number; category: string; kind?: string; label: string
  amount: number | null; hours?: number; detail: string; action_route: string
}
interface Impact {
  headline: {
    claims_revenue_at_stake: number
    money_savings_opportunity: number
    efficiency_hours_saved_mtd: number
    claims_paid_mtd: number
  }
  items: ImpactItem[]
}
interface DrillSource {
  type: string; id?: string; patient_id?: string; patient_name?: string
  claim_number?: string | null; status?: string; total_billed?: number
  total_paid?: number | null; denial_reason?: string | null; service_date?: string | null
  balance?: number; task?: string; label?: string; run_date?: string | null
  items_processed?: number; summary?: string; route?: string
}
interface Drilldown { kind: string; method: string; count: number; sources: DrillSource[] }

function money(n: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n)
}

const CAT_STYLE: Record<string, { color: string; label: string }> = {
  claims: { color: 'text-teal-700', label: 'Claims' },
  savings: { color: 'text-emerald-700', label: 'Savings' },
  efficiency: { color: 'text-violet-700', label: 'Efficiency' },
}

export default function PracticeImpact() {
  const navigate = useNavigate()
  const [impact, setImpact] = useState<Impact | null>(null)
  const [loading, setLoading] = useState(true)
  const [drillItem, setDrillItem] = useState<ImpactItem | null>(null)
  const [drill, setDrill] = useState<Drilldown | null>(null)
  const [drillLoading, setDrillLoading] = useState(false)

  useEffect(() => {
    api.getPracticeImpact().then(async r => {
      if (r.ok) setImpact(await r.json())
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  // Drill down into the source claims/findings behind an AI insight (shows how & where).
  async function openDrilldown(item: ImpactItem) {
    if (!item.kind) { navigate(item.action_route); return }
    setDrillItem(item)
    setDrill(null)
    setDrillLoading(true)
    try {
      const r = await api.getPracticeImpactDrilldown(item.kind)
      if (r.ok) setDrill(await r.json())
    } catch { /* handled */ }
    setDrillLoading(false)
  }

  const hl = impact?.headline

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="practice-impact">
      <div className="px-5 py-3 border-b border-gray-100 bg-gradient-to-r from-teal-50 to-white">
        <h3 className="text-sm font-semibold text-gray-900">OrthoFlow AI — Practice Impact</h3>
        <p className="text-[11px] text-gray-500">Claims first, then savings, then efficiency</p>
      </div>

      {loading ? (
        <div className="p-5 grid grid-cols-3 gap-3">{[1, 2, 3].map(i => <div key={i} className="h-16 bg-gray-50 rounded-xl animate-pulse" />)}</div>
      ) : hl ? (
        <>
          {/* Three-priority headline */}
          <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-gray-100">
            <div className="p-4" data-testid="impact-claims">
              <div className="flex items-center gap-1.5 mb-1"><TrendingUp size={14} className="text-teal-500" /><span className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Claims / Revenue</span></div>
              <p className="text-2xl font-bold text-teal-700">{money(hl.claims_revenue_at_stake)}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">at stake · {money(hl.claims_paid_mtd)} paid MTD</p>
            </div>
            <div className="p-4" data-testid="impact-savings">
              <div className="flex items-center gap-1.5 mb-1"><PiggyBank size={14} className="text-emerald-500" /><span className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Money Savings</span></div>
              <p className="text-2xl font-bold text-emerald-700">{money(hl.money_savings_opportunity)}</p>
              <p className="text-[11px] text-gray-500 mt-0.5">collectible + denials avoided</p>
            </div>
            <div className="p-4" data-testid="impact-efficiency">
              <div className="flex items-center gap-1.5 mb-1"><Timer size={14} className="text-violet-500" /><span className="text-[11px] uppercase tracking-wide text-gray-400 font-semibold">Efficiency</span></div>
              <p className="text-2xl font-bold text-violet-700">{hl.efficiency_hours_saved_mtd}h</p>
              <p className="text-[11px] text-gray-500 mt-0.5">staff time saved this month</p>
            </div>
          </div>

          {/* Prioritized $ items */}
          <div className="border-t border-gray-100 p-3 space-y-2">
            {(impact?.items || []).map((it, i) => {
              const s = CAT_STYLE[it.category] || CAT_STYLE.claims
              return (
                <button
                  key={i}
                  data-testid={`impact-item-${it.category}`}
                  onClick={() => openDrilldown(it)}
                  className="w-full text-left flex items-center gap-3 rounded-xl border border-gray-200/70 px-3 py-2.5 hover:shadow-sm hover:bg-gray-50 transition-all"
                >
                  <FileText size={15} className={`shrink-0 ${s.color}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{it.label}</p>
                    <p className="text-xs text-gray-500 leading-snug">{it.detail}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className={`text-sm font-bold ${s.color}`}>
                      {it.amount != null ? money(it.amount) : (it.hours != null ? `${it.hours}h` : '')}
                    </span>
                  </div>
                  <ChevronRight size={15} className="text-gray-300 shrink-0" />
                </button>
              )
            })}
          </div>
        </>
      ) : (
        <p className="p-5 text-sm text-gray-400">Impact data unavailable.</p>
      )}

      {/* AI insight drill-down — shows the exact source claims/findings behind the number */}
      {drillItem && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-4"
          onClick={() => setDrillItem(null)}
          data-testid="impact-drilldown"
        >
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-2xl max-h-[85vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 sticky top-0 bg-white">
              <div>
                <h3 className="font-semibold text-gray-900">{drillItem.label}</h3>
                <p className="text-[11px] text-gray-500 mt-0.5">{drillItem.detail}</p>
              </div>
              <button data-testid="impact-drilldown-close" onClick={() => setDrillItem(null)} className="text-gray-400 hover:text-gray-600"><X size={18} /></button>
            </div>
            <div className="p-5">
              {drill?.method && (
                <p className="text-xs text-gray-600 bg-gray-50 border border-gray-100 rounded-lg px-3 py-2 mb-3">
                  <span className="font-semibold">How this was calculated:</span> {drill.method}
                </p>
              )}
              {drillLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-400 py-4"><Loader2 size={14} className="animate-spin" /> Loading source records…</div>
              ) : !drill || drill.sources.length === 0 ? (
                <p className="text-sm text-gray-400 py-2">No source records found.</p>
              ) : (
                <div className="space-y-2" data-testid="impact-drilldown-sources">
                  {drill.sources.map((s, idx) => (
                    <button
                      key={s.id || idx}
                      onClick={() => { if (s.route) { setDrillItem(null); navigate(s.route) } }}
                      className="w-full text-left flex items-center gap-3 rounded-xl border border-gray-200/70 px-3 py-2.5 hover:bg-gray-50 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        {s.type === 'claim' && (
                          <>
                            <p className="text-sm font-medium text-gray-900">{s.patient_name} · {s.claim_number || 'Draft claim'}</p>
                            <p className="text-xs text-gray-500">
                              {s.status} · Billed {money(s.total_billed || 0)}
                              {s.service_date ? ` · ${s.service_date}` : ''}
                              {s.denial_reason ? ` · Denial: ${s.denial_reason}` : ''}
                            </p>
                          </>
                        )}
                        {s.type === 'balance' && (
                          <>
                            <p className="text-sm font-medium text-gray-900">{s.patient_name}</p>
                            <p className="text-xs text-gray-500">Outstanding balance {money(s.balance || 0)}</p>
                          </>
                        )}
                        {s.type === 'automation_run' && (
                          <>
                            <p className="text-sm font-medium text-gray-900">{s.label || s.task}</p>
                            <p className="text-xs text-gray-500">{s.run_date} · {s.items_processed} processed · {s.summary}</p>
                          </>
                        )}
                      </div>
                      {s.route && <ChevronRight size={15} className="text-gray-300 shrink-0" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
