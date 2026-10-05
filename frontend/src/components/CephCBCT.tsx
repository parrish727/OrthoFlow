import { useState, useEffect, useCallback, useRef } from 'react'
import { Box, Upload, Loader2, Sparkles } from 'lucide-react'
import { api } from '../lib/api'

// 3D CBCT panel (Phase F) — BETA, supervised. Ingest a CBCT DICOM (e.g. exported from Romexis),
// then (manually or via the self-hosted model when wired) landmark it; interpretation uses the
// higher-tier Anthropic model. 3D landmark editing is advanced; this panel covers ingest + status
// + interpretation + listing. All clinician-reviewed.

interface Scan {
  id: string; status: string; source_software: string | null
  measurements_3d: Record<string, { label: string; value: number | null; unit: string; status: string }>
  interpretation: string | null; created_at: string | null
}

export default function CephCBCT({ patientId, testId = 'ceph-cbct' }: { patientId: string; testId?: string }) {
  const [scans, setScans] = useState<Scan[]>([])
  const [mode, setMode] = useState<string>('manual')
  const [interpModel, setInterpModel] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  const load = useCallback(async () => {
    const [s, g] = await Promise.all([api.getPatientCbctScans(patientId), api.getCbctGeometryStatus()])
    if (s.ok) { const d = await s.json(); setScans(d.scans || []) }
    if (g.ok) { const d = await g.json(); setMode(d.mode); setInterpModel(d.interpretation_model || '') }
  }, [patientId])

  useEffect(() => { load() }, [load])

  async function upload(file: File) {
    setBusy(true); setMsg('')
    try {
      const res = await api.ingestCbct(patientId, file, 'Romexis/Planmeca')
      if (res.ok) { await load(); setMsg('CBCT uploaded — landmark & interpret (beta)') }
      else { const e = await res.json().catch(() => ({})); setMsg(e.detail || 'Upload failed') }
    } catch { setMsg('Upload failed') }
    setBusy(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  async function interpret(scanId: string) {
    setBusy(true)
    const res = await api.interpretCbct(scanId)
    if (res.ok) await load(); else { const e = await res.json().catch(() => ({})); setMsg(e.detail || 'Interpretation unavailable') }
    setBusy(false)
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4" data-testid={testId}>
      <div className="flex items-center gap-2 mb-1">
        <Box size={16} className="text-indigo-600" />
        <h3 className="text-sm font-semibold text-gray-800">3D CBCT Analysis</h3>
        <span className="text-[9px] font-bold text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded-full">BETA</span>
      </div>
      <p className="text-[11px] text-gray-400 mb-3">
        3D auto-landmarking: <b className="text-gray-600">{mode}</b>{interpModel ? ` · interpretation by ${interpModel}` : ''}. Supervised, clinician-reviewed.
      </p>

      <input ref={fileRef} type="file" accept=".dcm,application/dicom,application/octet-stream" className="hidden"
        data-testid="cbct-upload-input" onChange={e => { const f = e.target.files?.[0]; if (f) upload(f) }} />
      <button data-testid="cbct-upload-btn" onClick={() => fileRef.current?.click()} disabled={busy}
        className="flex items-center gap-1.5 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 px-3 py-2 rounded-lg">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} Upload CBCT (DICOM)
      </button>
      {msg && <p className="text-[11px] text-indigo-600 mt-1.5">{msg}</p>}

      {scans.map(s => (
        <div key={s.id} className="border-t border-gray-100 pt-2 mt-3 text-xs" data-testid={`cbct-${s.id}`}>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">{s.created_at?.slice(0, 10)} · {s.source_software || 'CBCT'} · {s.status}</span>
            {s.status !== 'interpreted' && Object.keys(s.measurements_3d || {}).length > 0 && (
              <button data-testid={`cbct-interpret-${s.id}`} onClick={() => interpret(s.id)} className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium">
                <Sparkles size={11} /> Interpret
              </button>
            )}
          </div>
          {s.interpretation && <p className="text-[11px] text-gray-600 mt-1.5 whitespace-pre-wrap line-clamp-6">{s.interpretation.slice(0, 400)}{s.interpretation.length > 400 ? '…' : ''}</p>}
        </div>
      ))}
    </div>
  )
}
