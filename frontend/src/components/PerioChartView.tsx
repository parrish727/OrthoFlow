/**
 * PerioChartView — 6-point probing depth charting with BOP, recession, and mobility.
 * Fetches from /api/v1/perio/patients/{id}/exams and /api/v1/perio/patients/{id}/summary
 */
import { useState, useEffect, useCallback } from 'react'
import { Plus, TrendingDown, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
function authFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('token')
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...opts.headers },
  })
}

interface PerioReading {
  tooth_number: number
  site: 'DB' | 'B' | 'MB' | 'DL' | 'L' | 'ML'
  probing_depth: number
  recession: number
  bleeding_on_probing: boolean
  suppuration: boolean
  plaque: boolean
  furcation_grade: number | null
  mobility_grade: number | null
}

interface PerioExam {
  id: string
  exam_date: string
  notes: string | null
  readings: PerioReading[]
}

interface PerioSummary {
  avg_probing_depth: number
  bop_percentage: number
  deep_pockets_count: number
  total_readings: number
  improvement_vs_prior: number | null
}

const SITES = ['DB', 'B', 'MB', 'DL', 'L', 'ML'] as const
const UPPER_TEETH = [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16]
const LOWER_TEETH = [32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17]

function depthColor(depth: number): string {
  if (depth <= 3) return 'bg-green-100 text-green-800'
  if (depth <= 5) return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}

function depthBorderColor(depth: number): string {
  if (depth <= 3) return 'border-green-300'
  if (depth <= 5) return 'border-amber-300'
  return 'border-red-400'
}

export default function PerioChartView({ patientId }: { patientId: string }) {
  const [exams, setExams] = useState<PerioExam[]>([])
  const [summary, setSummary] = useState<PerioSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedExam, setSelectedExam] = useState<PerioExam | null>(null)
  const [showNewExam, setShowNewExam] = useState(false)
  const [newReadings, setNewReadings] = useState<Record<string, number>>({})
  const [newBOP, setNewBOP] = useState<Set<string>>(new Set())
  const [saving, setSaving] = useState(false)

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [examsRes, summaryRes] = await Promise.all([
        authFetch(`/api/v1/perio/patients/${patientId}/exams`),
        authFetch(`/api/v1/perio/patients/${patientId}/summary`)
      ])
      if (examsRes.ok) {
        const data = await examsRes.json()
        setExams(data)
        if (data.length > 0) setSelectedExam(data[0])
      }
      if (summaryRes.ok) {
        setSummary(await summaryRes.json())
      }
    } catch { /* silent */ }
    setLoading(false)
  }, [patientId])

  useEffect(() => { fetchData() }, [fetchData])

  const handleCreateExam = async () => {
    setSaving(true)
    try {
      const createRes = await authFetch(`/api/v1/perio/patients/${patientId}/exams`, {
        method: 'POST',
        body: JSON.stringify({ exam_date: new Date().toISOString().split('T')[0], notes: null })
      })
      if (createRes.ok) {
        const exam = await createRes.json()
        // Build readings from form
        const readings: Partial<PerioReading>[] = []
        for (const key of Object.keys(newReadings)) {
          const [toothStr, site] = key.split('-')
          readings.push({
            tooth_number: parseInt(toothStr),
            site: site as PerioReading['site'],
            probing_depth: newReadings[key],
            recession: 0,
            bleeding_on_probing: newBOP.has(key),
            suppuration: false,
            plaque: false,
            furcation_grade: null,
            mobility_grade: null,
          })
        }
        if (readings.length > 0) {
          await authFetch(`/api/v1/perio/exams/${exam.id}/readings`, {
            method: 'POST',
            body: JSON.stringify({ readings })
          })
        }
        setShowNewExam(false)
        setNewReadings({})
        setNewBOP(new Set())
        fetchData()
      }
    } catch { /* silent */ }
    setSaving(false)
  }

  if (loading) return <div className="p-8 text-center text-sm text-gray-400">Loading perio chart...</div>

  // Build readings map for selected exam
  const readingsMap: Record<string, PerioReading> = {}
  if (selectedExam?.readings) {
    selectedExam.readings.forEach(r => {
      readingsMap[`${r.tooth_number}-${r.site}`] = r
    })
  }

  return (
    <div className="p-5 space-y-4">
      {/* Summary Banner */}
      {summary && summary.total_readings > 0 && (
        <div className="grid grid-cols-4 gap-3">
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-lg font-semibold text-gray-900">{summary.avg_probing_depth.toFixed(1)}mm</div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wide">Avg Depth</div>
          </div>
          <div className={`rounded-xl p-3 text-center ${summary.bop_percentage > 20 ? 'bg-red-50' : 'bg-green-50'}`}>
            <div className={`text-lg font-semibold ${summary.bop_percentage > 20 ? 'text-red-700' : 'text-green-700'}`}>
              {summary.bop_percentage.toFixed(0)}%
            </div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wide">BOP</div>
          </div>
          <div className={`rounded-xl p-3 text-center ${summary.deep_pockets_count > 0 ? 'bg-amber-50' : 'bg-green-50'}`}>
            <div className={`text-lg font-semibold ${summary.deep_pockets_count > 0 ? 'text-amber-700' : 'text-green-700'}`}>
              {summary.deep_pockets_count}
            </div>
            <div className="text-[10px] text-gray-500 uppercase tracking-wide">Deep Pockets (≥5mm)</div>
          </div>
          <div className="bg-gray-50 rounded-xl p-3 text-center">
            {summary.improvement_vs_prior !== null ? (
              <>
                <div className={`text-lg font-semibold flex items-center justify-center gap-1 ${summary.improvement_vs_prior > 0 ? 'text-green-700' : 'text-red-700'}`}>
                  {summary.improvement_vs_prior > 0 ? <TrendingDown size={14} /> : <TrendingUp size={14} />}
                  {Math.abs(summary.improvement_vs_prior).toFixed(1)}mm
                </div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wide">vs Prior</div>
              </>
            ) : (
              <>
                <div className="text-lg font-semibold text-gray-400">—</div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wide">No Prior</div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Exam selector + New Exam button */}
      <div className="flex items-center gap-3">
        {exams.length > 0 && (
          <select
            value={selectedExam?.id || ''}
            onChange={e => setSelectedExam(exams.find(ex => ex.id === e.target.value) || null)}
            className="text-xs border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
          >
            {exams.map(ex => (
              <option key={ex.id} value={ex.id}>
                {new Date(ex.exam_date).toLocaleDateString()} {ex.notes ? `— ${ex.notes}` : ''}
              </option>
            ))}
          </select>
        )}
        <button
          onClick={() => setShowNewExam(!showNewExam)}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium bg-orange-50 text-orange-700 rounded-lg hover:bg-orange-100 transition-colors"
        >
          <Plus size={12} /> New Exam
        </button>
      </div>

      {/* New Exam Entry Form */}
      {showNewExam && (
        <div className="border border-orange-200 rounded-xl p-4 bg-orange-50/50 space-y-3">
          <div className="text-xs font-medium text-orange-800 mb-2">
            Enter probing depths (tap cells to toggle BOP)
          </div>
          <ProbeEntryGrid
            readings={newReadings}
            bop={newBOP}
            onDepthChange={(key, val) => setNewReadings(r => ({ ...r, [key]: val }))}
            onBOPToggle={(key) => {
              setNewBOP(prev => {
                const next = new Set(prev)
                next.has(key) ? next.delete(key) : next.add(key)
                return next
              })
            }}
          />
          <div className="flex gap-2 pt-2">
            <button
              onClick={handleCreateExam}
              disabled={saving || Object.keys(newReadings).length === 0}
              className="px-4 py-2 text-xs font-medium bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : 'Save Exam'}
            </button>
            <button
              onClick={() => { setShowNewExam(false); setNewReadings({}); setNewBOP(new Set()) }}
              className="px-4 py-2 text-xs text-gray-600 rounded-lg hover:bg-gray-100"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Probing Chart Display */}
      {selectedExam && Object.keys(readingsMap).length > 0 ? (
        <div className="space-y-4">
          {/* Upper Arch */}
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Upper Arch (Buccal / Lingual)</div>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] border-collapse">
                <thead>
                  <tr>
                    <th className="px-1 py-0.5 text-left text-gray-400 w-8">Site</th>
                    {UPPER_TEETH.map(t => (
                      <th key={t} className="px-0.5 py-0.5 text-center text-gray-500 font-medium w-7">#{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SITES.slice(0, 3).map(site => (
                    <tr key={`upper-${site}`}>
                      <td className="px-1 py-0.5 text-gray-400 font-medium">{site}</td>
                      {UPPER_TEETH.map(tooth => {
                        const r = readingsMap[`${tooth}-${site}`]
                        return (
                          <td key={`${tooth}-${site}`} className="px-0.5 py-0.5 text-center">
                            {r ? (
                              <span className={`inline-block w-5 h-5 leading-5 rounded text-[9px] font-medium ${depthColor(r.probing_depth)} ${r.bleeding_on_probing ? 'ring-1 ring-red-400' : ''}`}>
                                {r.probing_depth}
                              </span>
                            ) : (
                              <span className="inline-block w-5 h-5 leading-5 text-gray-200">—</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                  {SITES.slice(3).map(site => (
                    <tr key={`upper-${site}`} className={site === 'DL' ? 'border-t border-gray-100' : ''}>
                      <td className="px-1 py-0.5 text-gray-400 font-medium">{site}</td>
                      {UPPER_TEETH.map(tooth => {
                        const r = readingsMap[`${tooth}-${site}`]
                        return (
                          <td key={`${tooth}-${site}`} className="px-0.5 py-0.5 text-center">
                            {r ? (
                              <span className={`inline-block w-5 h-5 leading-5 rounded text-[9px] font-medium ${depthColor(r.probing_depth)} ${r.bleeding_on_probing ? 'ring-1 ring-red-400' : ''}`}>
                                {r.probing_depth}
                              </span>
                            ) : (
                              <span className="inline-block w-5 h-5 leading-5 text-gray-200">—</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Lower Arch */}
          <div>
            <div className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">Lower Arch (Buccal / Lingual)</div>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px] border-collapse">
                <thead>
                  <tr>
                    <th className="px-1 py-0.5 text-left text-gray-400 w-8">Site</th>
                    {LOWER_TEETH.map(t => (
                      <th key={t} className="px-0.5 py-0.5 text-center text-gray-500 font-medium w-7">#{t}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SITES.slice(0, 3).map(site => (
                    <tr key={`lower-${site}`}>
                      <td className="px-1 py-0.5 text-gray-400 font-medium">{site}</td>
                      {LOWER_TEETH.map(tooth => {
                        const r = readingsMap[`${tooth}-${site}`]
                        return (
                          <td key={`${tooth}-${site}`} className="px-0.5 py-0.5 text-center">
                            {r ? (
                              <span className={`inline-block w-5 h-5 leading-5 rounded text-[9px] font-medium ${depthColor(r.probing_depth)} ${r.bleeding_on_probing ? 'ring-1 ring-red-400' : ''}`}>
                                {r.probing_depth}
                              </span>
                            ) : (
                              <span className="inline-block w-5 h-5 leading-5 text-gray-200">—</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                  {SITES.slice(3).map(site => (
                    <tr key={`lower-${site}`} className={site === 'DL' ? 'border-t border-gray-100' : ''}>
                      <td className="px-1 py-0.5 text-gray-400 font-medium">{site}</td>
                      {LOWER_TEETH.map(tooth => {
                        const r = readingsMap[`${tooth}-${site}`]
                        return (
                          <td key={`${tooth}-${site}`} className="px-0.5 py-0.5 text-center">
                            {r ? (
                              <span className={`inline-block w-5 h-5 leading-5 rounded text-[9px] font-medium ${depthColor(r.probing_depth)} ${r.bleeding_on_probing ? 'ring-1 ring-red-400' : ''}`}>
                                {r.probing_depth}
                              </span>
                            ) : (
                              <span className="inline-block w-5 h-5 leading-5 text-gray-200">—</span>
                            )}
                          </td>
                        )
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center gap-4 text-[10px] text-gray-500 pt-2 border-t border-gray-100">
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-green-100 border border-green-300" /> 1-3mm</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-amber-100 border border-amber-300" /> 4-5mm</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-red-100 border border-red-400" /> 6mm+</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 rounded bg-white ring-1 ring-red-400" /> BOP</span>
          </div>
        </div>
      ) : !showNewExam ? (
        <div className="text-center py-12">
          <AlertTriangle size={20} className="mx-auto text-gray-300 mb-2" />
          <p className="text-sm text-gray-400 mb-1">No periodontal exams recorded</p>
          <p className="text-xs text-gray-300">Click "New Exam" to start 6-point probing</p>
        </div>
      ) : null}
    </div>
  )
}

/** Compact inline probing entry grid for new exams */
function ProbeEntryGrid({
  readings,
  bop,
  onDepthChange,
  onBOPToggle
}: {
  readings: Record<string, number>
  bop: Set<string>
  onDepthChange: (key: string, val: number) => void
  onBOPToggle: (key: string) => void
}) {
  const [activeTooth, setActiveTooth] = useState<number | null>(null)

  return (
    <div className="space-y-3">
      {/* Quick tooth selector */}
      <div>
        <div className="text-[10px] text-gray-500 mb-1">Select tooth to chart:</div>
        <div className="flex flex-wrap gap-1">
          {[...UPPER_TEETH, ...LOWER_TEETH].map(t => (
            <button
              key={t}
              onClick={() => setActiveTooth(t)}
              className={`w-6 h-6 text-[9px] rounded font-medium transition-colors ${
                activeTooth === t
                  ? 'bg-orange-600 text-white'
                  : Object.keys(readings).some(k => k.startsWith(`${t}-`))
                    ? 'bg-orange-100 text-orange-700'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Per-site entry for active tooth */}
      {activeTooth && (
        <div className="bg-white rounded-lg border border-gray-200 p-3">
          <div className="text-xs font-medium text-gray-700 mb-2">Tooth #{activeTooth} — 6-Point Probing</div>
          <div className="grid grid-cols-6 gap-2">
            {SITES.map(site => {
              const key = `${activeTooth}-${site}`
              return (
                <div key={site} className="text-center">
                  <div className="text-[9px] text-gray-400 mb-0.5">{site}</div>
                  <input
                    type="number"
                    min={1}
                    max={12}
                    value={readings[key] || ''}
                    onChange={e => onDepthChange(key, parseInt(e.target.value) || 0)}
                    className={`w-full text-center text-xs border rounded py-1 ${
                      readings[key] ? depthBorderColor(readings[key]) : 'border-gray-200'
                    }`}
                    placeholder="—"
                  />
                  <button
                    onClick={() => onBOPToggle(key)}
                    className={`mt-1 w-full text-[8px] py-0.5 rounded transition-colors ${
                      bop.has(key) ? 'bg-red-100 text-red-600 font-medium' : 'bg-gray-50 text-gray-400'
                    }`}
                  >
                    BOP
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
