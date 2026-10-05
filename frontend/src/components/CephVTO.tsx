import { useState, useEffect, useCallback } from 'react'
import { Target, Loader2, Check } from 'lucide-react'
import { api } from '../lib/api'

// VTO (Visual Treatment Objective) panel — Phase E. Project a predicted treatment target from a
// finalized tracing (growth + planned mechanics) with a Holdaway soft-tissue response. PREDICTION,
// clinician-reviewed. Schematic now; photo-realistic morph scaffolded.

interface Tracing { id: string; analysis_type: string; status: string; created_at: string | null }
interface VTO {
  id: string; status: string; unit: string
  params: Record<string, number>
  soft_tissue: { assumptions?: Record<string, unknown>; disclaimer?: string }
  finalized_at: string | null; created_at: string | null
}

export default function CephVTO({ patientId, testId = 'ceph-vto' }: { patientId: string; testId?: string }) {
  const [tracings, setTracings] = useState<Tracing[]>([])
  const [vtos, setVtos] = useState<VTO[]>([])
  const [src, setSrc] = useState('')
  const [growth, setGrowth] = useState('12')
  const [u1, setU1] = useState('0')
  const [l1, setL1] = useState('0')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')

  const load = useCallback(async () => {
    const [t, v] = await Promise.all([api.getPatientTracings(patientId), api.getCephVtos(patientId)])
    if (t.ok) { const d = await t.json(); setTracings((d.tracings || []).filter((x: Tracing) => x.status === 'finalized')) }
    if (v.ok) { const d = await v.json(); setVtos(d.vtos || []) }
  }, [patientId])

  useEffect(() => { load() }, [load])

  async function project() {
    if (!src) { setMsg('Pick a finalized tracing'); return }
    setBusy(true); setMsg('')
    try {
      const res = await api.createCephVto({
        source_tracing_id: src,
        growth_months: Number(growth) || 0,
        u1_retraction_mm: Number(u1) || 0,
        l1_retraction_mm: Number(l1) || 0,
      })
      if (res.ok) { await load(); setMsg('VTO projected — review before sharing') }
      else { const e = await res.json().catch(() => ({})); setMsg(e.detail || 'Failed') }
    } catch { setMsg('Failed') }
    setBusy(false)
  }

  async function finalize(id: string) {
    const res = await api.finalizeCephVto(id)
    if (res.ok) load()
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4" data-testid={testId}>
      <div className="flex items-center gap-2 mb-3">
        <Target size={16} className="text-violet-600" />
        <h3 className="text-sm font-semibold text-gray-800">Visual Treatment Objective (VTO)</h3>
      </div>

      {tracings.length === 0 ? (
        <p className="text-xs text-gray-400">Finalize a tracing to project a treatment objective.</p>
      ) : (
        <div className="space-y-2">
          <select data-testid="vto-source" value={src} onChange={e => setSrc(e.target.value)} className="w-full text-sm border border-gray-200 rounded-lg px-2 py-1.5">
            <option value="">Source tracing…</option>
            {tracings.map(t => <option key={t.id} value={t.id}>{t.created_at?.slice(0, 10)} · {t.analysis_type}</option>)}
          </select>
          <div className="grid grid-cols-3 gap-2">
            <label className="text-[11px] text-gray-500">Growth (mo)
              <input data-testid="vto-growth" type="number" value={growth} onChange={e => setGrowth(e.target.value)} className="block w-full mt-0.5 text-sm border border-gray-200 rounded-lg px-2 py-1" />
            </label>
            <label className="text-[11px] text-gray-500">U1 retract (mm)
              <input data-testid="vto-u1" type="number" value={u1} onChange={e => setU1(e.target.value)} className="block w-full mt-0.5 text-sm border border-gray-200 rounded-lg px-2 py-1" />
            </label>
            <label className="text-[11px] text-gray-500">L1 retract (mm)
              <input data-testid="vto-l1" type="number" value={l1} onChange={e => setL1(e.target.value)} className="block w-full mt-0.5 text-sm border border-gray-200 rounded-lg px-2 py-1" />
            </label>
          </div>
          <button data-testid="vto-project" onClick={project} disabled={busy}
            className="w-full flex items-center justify-center gap-1.5 text-sm font-medium text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50 px-3 py-2 rounded-lg">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Target size={14} />} Project VTO
          </button>
          {msg && <p className="text-[11px] text-violet-600">{msg}</p>}
        </div>
      )}

      {vtos.map(v => (
        <div key={v.id} className="border-t border-gray-100 pt-2 mt-3 text-xs" data-testid={`vto-${v.id}`}>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">{v.created_at?.slice(0, 10)} · {Object.entries(v.params).map(([k, val]) => `${k}=${val}`).join(', ')}</span>
            {v.status === 'finalized'
              ? <span className="text-emerald-700 font-medium flex items-center gap-1"><Check size={11} /> finalized</span>
              : <button data-testid={`vto-finalize-${v.id}`} onClick={() => finalize(v.id)} className="text-violet-600 hover:text-violet-800 font-medium">Finalize</button>}
          </div>
        </div>
      ))}
      <p className="text-[10px] text-gray-400 mt-3">Predicted objective for planning/communication — clinician-reviewed, not a guaranteed outcome. Photo-realistic morph coming; schematic profile today.</p>
    </div>
  )
}
