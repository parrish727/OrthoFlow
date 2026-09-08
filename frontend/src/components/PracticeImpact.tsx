import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, PiggyBank, Timer, FileText, ChevronRight } from 'lucide-react'
import { api } from '../lib/api'

interface ImpactItem {
  priority: number; category: string; label: string
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

  useEffect(() => {
    api.getPracticeImpact().then(async r => {
      if (r.ok) setImpact(await r.json())
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

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
                  onClick={() => navigate(it.action_route)}
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
    </div>
  )
}
