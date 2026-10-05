import { useState, useEffect, useCallback } from 'react'
import { GitCompare, Loader2, TrendingUp } from 'lucide-react'
import { api } from '../lib/api'

// Ceph progress tracking (Phase D) — superimpose two finalized tracings on stable reference points
// and show how each landmark moved over time (ICS-style). Growth + treatment change.

interface Tracing { id: string; analysis_type: string; status: string; created_at: string | null }
interface Delta { dx: number; dy: number; total: number }
interface Superimp {
  id: string; method: string; unit: string
  deltas: Record<string, Delta>
  summary: { unit?: string; landmarks_compared?: number; landmarks_moved?: number; max_change?: number; notable?: string[] }
  created_at: string | null
}

export default function CephProgress({ patientId, testId = 'ceph-progress' }: { patientId: string; testId?: string }) {
  const [tracings, setTracings] = useState<Tracing[]>([])
  const [superimps, setSuperimps] = useState<Superimp[]>([])
  const [baseline, setBaseline] = useState('')
  const [follow, setFollow] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    const [tRes, sRes] = await Promise.all([
      api.getPatientTracings(patientId),
      api.getCephSuperimpositions(patientId),
    ])
    if (tRes.ok) { const d = await tRes.json(); setTracings((d.tracings || []).filter((t: Tracing) => t.status === 'finalized')) }
    if (sRes.ok) { const d = await sRes.json(); setSuperimps(d.superimpositions || []) }
  }, [patientId])

  useEffect(() => { load() }, [load])

  async function run() {
    if (!baseline || !follow || baseline === follow) { setMsg('Pick two different finalized tracings'); return }
    setBusy(true); setMsg('')
    try {
      const res = await api.createCephSuperimposition({ baseline_tracing_id: baseline, follow_tracing_id: follow, method: 'sn' })
      if (res.ok) { await load(); setMsg('Superimposition complete') }
      else { const e = await res.json().catch(() => ({})); setMsg(e.detail || 'Failed') }
    } catch { setMsg('Failed') }
    setBusy(false)
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4" data-testid={testId}>
      <div className="flex items-center gap-2 mb-3">
        <GitCompare size={16} className="text-teal-600" />
        <h3 className="text-sm font-semibold text-gray-800">Cephalometric Progress</h3>
      </div>

      {tracings.length < 2 ? (
        <p className="text-xs text-gray-400">Finalize at least two tracings to compare progress over time.</p>
      ) : (
        <div className="flex flex-wrap items-end gap-2 mb-3">
          <label className="text-xs text-gray-500">Baseline
            <select data-testid="superimp-baseline" value={baseline} onChange={e => setBaseline(e.target.value)} className="block mt-1 text-sm border border-gray-200 rounded-lg px-2 py-1.5">
              <option value="">—</option>
              {tracings.map(t => <option key={t.id} value={t.id}>{t.created_at?.slice(0, 10)} · {t.analysis_type}</option>)}
            </select>
          </label>
          <label className="text-xs text-gray-500">Follow-up
            <select data-testid="superimp-follow" value={follow} onChange={e => setFollow(e.target.value)} className="block mt-1 text-sm border border-gray-200 rounded-lg px-2 py-1.5">
              <option value="">—</option>
              {tracings.map(t => <option key={t.id} value={t.id}>{t.created_at?.slice(0, 10)} · {t.analysis_type}</option>)}
            </select>
          </label>
          <button data-testid="superimp-run" onClick={run} disabled={busy}
            className="flex items-center gap-1.5 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50 px-3 py-2 rounded-lg">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <TrendingUp size={14} />} Compare
          </button>
          {msg && <span className="text-[11px] text-gray-500">{msg}</span>}
        </div>
      )}

      {superimps.map(s => (
        <div key={s.id} className="border-t border-gray-100 pt-3 mt-3" data-testid={`superimp-${s.id}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-500">{s.created_at?.slice(0, 10)} · registered on S–N · {s.unit}</span>
            <span className="text-[11px] font-medium text-teal-700">max change {s.summary.max_change?.toFixed(1)} {s.unit}</span>
          </div>
          <table className="w-full text-xs">
            <thead><tr className="text-gray-400 uppercase text-left"><th className="py-1">Landmark</th><th className="py-1 text-right">Δx</th><th className="py-1 text-right">Δy</th><th className="py-1 text-right">Total</th></tr></thead>
            <tbody>
              {Object.entries(s.deltas).sort((a, b) => b[1].total - a[1].total).map(([k, d]) => (
                <tr key={k} className="border-t border-gray-50">
                  <td className="py-1 text-gray-700 font-medium">{k}</td>
                  <td className="py-1 text-right text-gray-500">{d.dx}</td>
                  <td className="py-1 text-right text-gray-500">{d.dy}</td>
                  <td className={`py-1 text-right font-semibold ${d.total >= (s.unit === 'mm' ? 0.5 : 5) ? 'text-amber-600' : 'text-gray-400'}`}>{d.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <p className="text-[10px] text-gray-400 mt-3">Change is measured after registering on the anterior cranial base (S–N) — separating treatment/growth change from head position. Clinician-reviewed.</p>
    </div>
  )
}
