import { useState, useEffect, useRef, useCallback } from 'react'
import { Crosshair, Ruler, Check, Loader2, RotateCcw, Sparkles } from 'lucide-react'
import { api } from '../lib/api'

// Cephalometric tracing editor (Ceph Suite Phase A + B).
// Place landmarks on the ceph image, drag to refine (measurements recompute live), calibrate
// pixels→mm by marking a known distance, pick an analysis, optionally AI auto-trace (draft for
// doctor review, confidence-shaded), and finalize (doctor sign-off).

interface Pt { x: number; y: number; conf?: number | null }
interface Measure { label: string; value: number | null; unit: string; norm: number; sd: number; status: string }
interface Analysis { key: string; name: string; landmark_keys: string[]; measurement_keys: string[] }
interface Tracing {
  id: string
  analysis_type: string
  landmarks: Record<string, Pt>
  measurements: Record<string, Measure>
  calibration: { px_per_mm: number } | null
  status: string
}

const STATUS_COLOR: Record<string, string> = {
  normal: 'text-emerald-600', high: 'text-red-600', low: 'text-blue-600', missing: 'text-gray-300',
}

export default function CephTracingEditor({ imageId, patientId, imageUrl, testId = 'ceph-editor' }: { imageId: string; patientId: string; imageUrl: string; testId?: string }) {
  const [analyses, setAnalyses] = useState<Analysis[]>([])
  const [analysisKey, setAnalysisKey] = useState('abo')
  const [tracing, setTracing] = useState<Tracing | null>(null)
  const [activeLandmark, setActiveLandmark] = useState<string | null>(null)
  const [calibrating, setCalibrating] = useState(false)
  const [calibPts, setCalibPts] = useState<Pt[]>([])
  const [saving, setSaving] = useState(false)
  const [aiBusy, setAiBusy] = useState(false)
  const [aiMsg, setAiMsg] = useState('')
  const svgRef = useRef<SVGSVGElement>(null)

  const analysis = analyses.find(a => a.key === analysisKey)

  useEffect(() => {
    (async () => {
      const res = await api.getCephAnalyses()
      if (res.ok) { const d = await res.json(); setAnalyses(d.analyses || []) }
    })()
  }, [])

  // Create a draft tracing on mount (or load the most recent draft for this image).
  useEffect(() => {
    (async () => {
      const res = await api.createCephTracing({ image_id: imageId, analysis_type: analysisKey, landmarks: {} })
      if (res.ok) setTracing(await res.json())
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageId])

  const persist = useCallback(async (landmarks: Record<string, Pt>, extra?: { analysis_type?: string; calibration?: { px_per_mm: number } }) => {
    if (!tracing) return
    setSaving(true)
    const res = await api.updateCephTracing(tracing.id, { landmarks, ...extra })
    if (res.ok) setTracing(await res.json())
    setSaving(false)
  }, [tracing])

  function svgCoords(e: React.MouseEvent): Pt {
    const svg = svgRef.current!
    const rect = svg.getBoundingClientRect()
    const vb = svg.viewBox.baseVal
    return { x: ((e.clientX - rect.left) / rect.width) * vb.width, y: ((e.clientY - rect.top) / rect.height) * vb.height }
  }

  async function onSvgClick(e: React.MouseEvent) {
    const p = svgCoords(e)
    if (calibrating) {
      const next = [...calibPts, p]
      if (next.length === 2) {
        const px = Math.hypot(next[1].x - next[0].x, next[1].y - next[0].y)
        const mmStr = window.prompt(`Known real-world distance between the two points, in mm:`, '20')
        const mm = parseFloat(mmStr || '')
        if (mm > 0 && px > 0) await persist(tracing!.landmarks, { calibration: { px_per_mm: px / mm } })
        setCalibrating(false); setCalibPts([])
      } else { setCalibPts(next) }
      return
    }
    if (activeLandmark && tracing) {
      const landmarks = { ...tracing.landmarks, [activeLandmark]: p }
      // advance to next unplaced landmark for fast tracing
      const keys = analysis?.landmark_keys || []
      const nextKey = keys.find(k => k !== activeLandmark && !landmarks[k]) || null
      setActiveLandmark(nextKey)
      await persist(landmarks)
    }
  }

  async function onAnalysisChange(key: string) {
    setAnalysisKey(key)
    if (tracing) await persist(tracing.landmarks, { analysis_type: key })
  }

  async function finalize() {
    if (!tracing) return
    setSaving(true)
    const res = await api.finalizeCephTracing(tracing.id)
    if (res.ok) setTracing(await res.json())
    setSaving(false)
  }

  async function resetLandmark(k: string) {
    if (!tracing) return
    const landmarks = { ...tracing.landmarks }; delete landmarks[k]
    await persist(landmarks)
  }

  async function aiAutoTrace() {
    setAiBusy(true); setAiMsg('')
    try {
      const res = await api.autoLandmarkCeph({ image_id: imageId, analysis_type: analysisKey })
      if (res.ok) {
        setTracing(await res.json())
        setAiMsg('AI draft ready — review each point before finalizing')
      } else {
        const err = await res.json().catch(() => ({}))
        setAiMsg(err.detail || 'AI unavailable — trace manually')
      }
    } catch { setAiMsg('AI unavailable — trace manually') }
    setAiBusy(false)
  }

  const landmarks = tracing?.landmarks || {}
  const keys = analysis?.landmark_keys || []
  const placed = keys.filter(k => landmarks[k]).length
  const finalized = tracing?.status === 'finalized'

  return (
    <div className="grid lg:grid-cols-3 gap-4" data-testid={testId}>
      {/* Canvas */}
      <div className="lg:col-span-2 bg-black rounded-2xl overflow-hidden relative">
        <svg ref={svgRef} viewBox="0 0 1000 1000" className="w-full h-auto cursor-crosshair" onClick={onSvgClick} data-testid="ceph-canvas">
          <image href={imageUrl} x="0" y="0" width="1000" height="1000" preserveAspectRatio="xMidYMid meet" />
          {/* calibration points */}
          {calibPts.map((p, i) => (<circle key={i} cx={p.x} cy={p.y} r={6} fill="#f59e0b" />))}
          {calibPts.length === 2 && <line x1={calibPts[0].x} y1={calibPts[0].y} x2={calibPts[1].x} y2={calibPts[1].y} stroke="#f59e0b" strokeWidth={2} />}
          {/* landmarks */}
          {Object.entries(landmarks).map(([k, p]) => {
            const lowConf = typeof p.conf === 'number' && p.conf < 0.6
            return (
              <g key={k} data-testid={`ceph-landmark-${k}`}>
                <circle cx={p.x} cy={p.y} r={5} fill={activeLandmark === k ? '#14b8a6' : '#22d3ee'}
                  stroke={lowConf ? '#f59e0b' : '#0f172a'} strokeWidth={lowConf ? 2.5 : 1} />
                <text x={p.x + 8} y={p.y - 6} fill={lowConf ? '#fbbf24' : '#67e8f9'} fontSize={16} fontWeight={700}>
                  {k}{lowConf ? '?' : ''}
                </text>
              </g>
            )
          })}
        </svg>
        {saving && <div className="absolute top-2 right-2 text-white/80"><Loader2 size={16} className="animate-spin" /></div>}
      </div>

      {/* Controls + measurements */}
      <div className="space-y-3">
        <div className="bg-white rounded-2xl border border-gray-200/80 p-3">
          <label className="text-xs font-semibold text-gray-500 uppercase">Analysis</label>
          <select data-testid="ceph-analysis-select" value={analysisKey} onChange={e => onAnalysisChange(e.target.value)} disabled={finalized}
            className="w-full mt-1 text-sm border border-gray-200 rounded-lg px-2 py-1.5">
            {analyses.map(a => <option key={a.key} value={a.key}>{a.name}</option>)}
          </select>
          <div className="flex items-center gap-2 mt-2">
            <button data-testid="ceph-calibrate-btn" disabled={finalized} onClick={() => { setCalibrating(true); setCalibPts([]) }}
              className={`flex items-center gap-1 text-xs px-2 py-1.5 rounded-lg border ${calibrating ? 'bg-amber-500 text-white border-amber-500' : 'bg-white text-gray-700 border-gray-200'}`}>
              <Ruler size={12} /> {tracing?.calibration ? `${tracing.calibration.px_per_mm.toFixed(1)} px/mm` : 'Calibrate'}
            </button>
            <button data-testid="ceph-ai-trace-btn" disabled={finalized || aiBusy} onClick={aiAutoTrace}
              className="flex items-center gap-1 text-xs px-2 py-1.5 rounded-lg border bg-violet-600 text-white border-violet-600 hover:bg-violet-700 disabled:opacity-50">
              {aiBusy ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} AI Auto-Trace
            </button>
          </div>
          {aiMsg && <p className="text-[11px] text-violet-600 mt-1.5" data-testid="ceph-ai-msg">{aiMsg}</p>}
        </div>

        {/* Landmark palette */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-gray-500 uppercase">Landmarks</span>
            <span className="text-[10px] text-gray-400">{placed}/{keys.length} placed</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {keys.map(k => (
              <button key={k} data-testid={`ceph-landmark-btn-${k}`} disabled={finalized}
                onClick={() => setActiveLandmark(k === activeLandmark ? null : k)}
                className={`text-xs px-2 py-1 rounded-md border flex items-center gap-1 ${activeLandmark === k ? 'bg-teal-600 text-white border-teal-600' : landmarks[k] ? 'bg-teal-50 text-teal-700 border-teal-200' : 'bg-white text-gray-600 border-gray-200'}`}>
                {activeLandmark === k && <Crosshair size={10} />}{k}
                {landmarks[k] && <RotateCcw size={9} onClick={e => { e.stopPropagation(); resetLandmark(k) }} className="opacity-60 hover:opacity-100" />}
              </button>
            ))}
          </div>
          {activeLandmark && <p className="text-[11px] text-teal-600 mt-2">Click the image to place <b>{activeLandmark}</b></p>}
        </div>

        {/* Measurements */}
        <div className="bg-white rounded-2xl border border-gray-200/80 p-3" data-testid="ceph-measurements">
          <span className="text-xs font-semibold text-gray-500 uppercase">Measurements</span>
          <table className="w-full text-xs mt-2">
            <tbody>
              {Object.entries(tracing?.measurements || {}).map(([k, m]) => (
                <tr key={k} className="border-t border-gray-50" data-testid={`ceph-measure-${k}`}>
                  <td className="py-1 text-gray-600">{m.label}</td>
                  <td className={`py-1 text-right font-semibold ${STATUS_COLOR[m.status]}`}>
                    {m.value != null ? `${m.value}${m.unit === 'deg' ? '°' : m.unit === '%' ? '%' : ' ' + m.unit}` : '—'}
                  </td>
                  <td className="py-1 text-right text-[10px] text-gray-400">{m.norm}±{m.sd}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {tracing?.measurements && Object.values(tracing.measurements).some(m => m.unit === 'mm' && m.value === null) && !tracing?.calibration && (
            <p className="text-[10px] text-amber-600 mt-1">Calibrate to compute mm measurements.</p>
          )}
        </div>

        {!finalized ? (
          <button data-testid="ceph-finalize-btn" onClick={finalize} disabled={saving || placed === 0}
            className="w-full flex items-center justify-center gap-1.5 text-sm font-medium text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50 px-3 py-2 rounded-lg">
            <Check size={14} /> Finalize Tracing (doctor sign-off)
          </button>
        ) : (
          <div className="w-full text-center text-sm font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-lg py-2" data-testid="ceph-finalized">
            ✓ Finalized
          </div>
        )}
        <p className="text-[10px] text-gray-400">AI/manual tracings are clinical decision-support and require doctor review before use.</p>
      </div>
    </div>
  )
}
