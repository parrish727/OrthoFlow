import { useState, useEffect, useCallback } from 'react'
import { Zap, RefreshCw, CheckCircle2, FileText, CreditCard, ShieldCheck } from 'lucide-react'
import { api } from '../lib/api'

interface Run {
  id: string; run_date: string; task: string; label: string
  status: string; items_processed: number; summary: string
}

const TASK_ICON: Record<string, typeof FileText> = {
  recurring_claims: FileText,
  payment_poll: CreditCard,
  consult_verify: ShieldCheck,
}

export default function AutomationActivity() {
  const [runs, setRuns] = useState<Run[]>([])
  const [totalActions, setTotalActions] = useState(0)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)

  const load = useCallback(async () => {
    try {
      const r = await api.getAutomationActivity(7)
      if (r.ok) { const d = await r.json(); setRuns(d.runs || []); setTotalActions(d.total_actions || 0) }
    } catch { /* handled */ } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function runNow() {
    setRunning(true)
    try { await api.runAutomation(); await load() } catch { /* handled */ }
    setRunning(false)
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden" data-testid="automation-activity">
      <div className="px-5 py-3 border-b border-gray-100 flex items-center gap-2 bg-gradient-to-r from-teal-50 to-white">
        <Zap size={16} className="text-teal-500" />
        <h3 className="text-sm font-semibold text-gray-900">OrthoFlow handled this automatically</h3>
        {totalActions > 0 && (
          <span className="ml-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-100 text-teal-700">
            {totalActions} actions / 7d
          </span>
        )}
        <button
          data-testid="automation-run-now"
          onClick={runNow}
          disabled={running}
          className="ml-auto flex items-center gap-1 text-xs font-medium text-teal-600 hover:text-teal-700 disabled:opacity-50"
        >
          <RefreshCw size={13} className={running ? 'animate-spin' : ''} /> Run now
        </button>
      </div>
      <div className="p-3 space-y-2">
        {loading ? (
          <div className="space-y-2">{[1, 2, 3].map(i => <div key={i} className="h-12 bg-gray-50 rounded-xl animate-pulse" />)}</div>
        ) : runs.length === 0 ? (
          <p className="text-sm text-gray-400 py-4 px-2">No automated activity yet — it runs daily and after you click "Run now".</p>
        ) : (
          runs.slice(0, 6).map(r => {
            const Icon = TASK_ICON[r.task] || CheckCircle2
            return (
              <div key={r.id} className="flex items-start gap-2.5 rounded-xl border border-gray-200/70 px-3 py-2.5">
                <Icon size={15} className="text-teal-500 shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">{r.label}</p>
                  <p className="text-xs text-gray-500">{r.summary}</p>
                </div>
                <span className="text-[10px] text-gray-400 shrink-0">{r.run_date}</span>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
