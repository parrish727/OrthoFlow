import { useState, useEffect } from 'react'
import { Sparkles, Users, FileText, Loader2, TrendingUp, AlertTriangle, BarChart3, Brain, Clock, Target, DollarSign } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  last_name: string
}

interface HuddleInsight {
  patient_id: string
  patient_name: string
  status: string
  next_action: string
  priority: 'high' | 'medium' | 'low'
}

interface TimelinePrediction {
  predicted_months_remaining: number
  confidence: 'high' | 'medium' | 'low'
  milestones: { name: string; date: string; completed: boolean }[]
  delay_factors: string[]
}

interface DenialPattern {
  payer: string
  code: string
  count: number
  reason: string
}

interface DenialAnalysis {
  total_denied: number
  recovery_potential: number
  patterns: DenialPattern[]
  recommendations: string[]
}

interface Benchmark {
  phase: string
  avg_duration_months: number
}

export default function AIInsights() {
const [patients, setPatients] = useState<Patient[]>([])

  // Huddle state
  const [selectedPatientIds, setSelectedPatientIds] = useState<string[]>([])
  const [huddleInsights, setHuddleInsights] = useState<HuddleInsight[]>([])
  const [huddleLoading, setHuddleLoading] = useState(false)

  // Timeline state
  const [timelinePatientId, setTimelinePatientId] = useState('')
  const [timeline, setTimeline] = useState<TimelinePrediction | null>(null)
  const [timelineLoading, setTimelineLoading] = useState(false)

  // Denial state
  const [denialData, setDenialData] = useState<DenialAnalysis | null>(null)
  const [denialLoading, setDenialLoading] = useState(false)

  // Benchmark state
  const [benchmarks, setBenchmarks] = useState<Benchmark[]>([])
  const [benchmarkLoading, setBenchmarkLoading] = useState(false)
useEffect(() => {
    api.getPatients({ page: 1 }).then(async res => {
      if (res.ok) { const data = await res.json(); setPatients(data.patients || data.items || []) }
    })
  }, [])

  async function generateHuddleInsights() {
    if (selectedPatientIds.length === 0) return
    setHuddleLoading(true)
    const res = await api.aiBatchInsights({ patient_ids: selectedPatientIds })
    if (res.ok) {
      const data = await res.json()
      setHuddleInsights(data.insights || [])
    }
    setHuddleLoading(false)
  }

  async function loadTimeline() {
    if (!timelinePatientId) return
    setTimelineLoading(true)
    const res = await api.aiTimelinePredict(timelinePatientId)
    if (res.ok) {
      const data = await res.json()
      setTimeline(data)
    }
    setTimelineLoading(false)
  }

  async function loadDenialPatterns() {
    setDenialLoading(true)
    const res = await api.aiDenialPatterns()
    if (res.ok) {
      const data = await res.json()
      setDenialData(data)
    }
    setDenialLoading(false)
  }

  async function loadBenchmarks() {
    setBenchmarkLoading(true)
    const res = await api.aiBenchmarks()
    if (res.ok) {
      const data = await res.json()
      setBenchmarks(data.benchmarks || [])
    }
    setBenchmarkLoading(false)
  }

  useEffect(() => { loadDenialPatterns(); loadBenchmarks() }, [])

  function togglePatient(id: string) {
    setSelectedPatientIds(prev =>
      prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]
    )
  }

  function getPriorityBadge(priority: string) {
    switch (priority) {
      case 'high': return 'bg-red-100 text-red-700'
      case 'medium': return 'bg-amber-100 text-amber-700'
      case 'low': return 'bg-blue-100 text-blue-700'
      default: return 'bg-gray-100 text-gray-700'
    }
  }

  function getConfidenceColor(confidence: string) {
    switch (confidence) {
      case 'high': return 'text-emerald-600'
      case 'medium': return 'text-amber-600'
      case 'low': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  return (
    <>
      <div className="space-y-8">
        {/* Page Title */}
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">AI Intelligence Dashboard</h2>
          <p className="text-sm text-gray-500 mt-0.5">AI-powered insights for your practice</p>
        </div>

        {/* Morning Huddle */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <Target size={16} className="text-violet-500" />
            <h3 className="font-medium text-gray-800">Morning Huddle</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-500 mb-4">Select patients for today's huddle to generate AI insights</p>
            <div className="flex flex-wrap gap-2 mb-4 max-h-32 overflow-y-auto">
              {patients.map(p => (
                <button
                  key={p.id}
                  onClick={() => togglePatient(p.id)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    selectedPatientIds.includes(p.id)
                      ? 'bg-violet-100 border-violet-300 text-violet-700'
                      : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
                  }`}
                >
                  {p.first_name} {p.last_name}
                </button>
              ))}
            </div>
            <button
              onClick={generateHuddleInsights}
              disabled={huddleLoading || selectedPatientIds.length === 0}
              className="flex items-center gap-2 px-4 py-2 bg-violet-500 hover:bg-violet-600 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
            >
              {huddleLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Generate Insights
            </button>

            {huddleInsights.length > 0 && (
              <div className="mt-6 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100">
                      <th className="text-left py-3 px-3 font-medium text-gray-500">Patient</th>
                      <th className="text-left py-3 px-3 font-medium text-gray-500">Status</th>
                      <th className="text-left py-3 px-3 font-medium text-gray-500">Next Action</th>
                      <th className="text-left py-3 px-3 font-medium text-gray-500">Priority</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {huddleInsights.map((insight, idx) => (
                      <tr key={idx}>
                        <td className="py-3 px-3 font-medium text-gray-800">{insight.patient_name}</td>
                        <td className="py-3 px-3 text-gray-600">{insight.status}</td>
                        <td className="py-3 px-3 text-gray-600">{insight.next_action}</td>
                        <td className="py-3 px-3">
                          <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getPriorityBadge(insight.priority)}`}>
                            {insight.priority}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>

        {/* Treatment Timeline */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <Clock size={16} className="text-blue-500" />
            <h3 className="font-medium text-gray-800">Treatment Timeline</h3>
          </div>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-4">
              <select
                value={timelinePatientId}
                onChange={(e) => setTimelinePatientId(e.target.value)}
                className="flex-1 max-w-xs px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="">Select patient...</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              <button
                onClick={loadTimeline}
                disabled={timelineLoading || !timelinePatientId}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                {timelineLoading ? <Loader2 size={16} className="animate-spin" /> : <TrendingUp size={16} />}
                Predict Timeline
              </button>
            </div>

            {timeline && (
              <div className="mt-4 space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-xs text-gray-500 mb-1">Predicted Months Remaining</p>
                    <p className="text-2xl font-semibold text-gray-900">{timeline.predicted_months_remaining}</p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-xs text-gray-500 mb-1">Confidence Level</p>
                    <p className={`text-2xl font-semibold capitalize ${getConfidenceColor(timeline.confidence)}`}>{timeline.confidence}</p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4">
                    <p className="text-xs text-gray-500 mb-1">Milestones</p>
                    <p className="text-2xl font-semibold text-gray-900">{timeline.milestones.length}</p>
                  </div>
                </div>

                {/* Vertical Timeline */}
                {timeline.milestones.length > 0 && (
                  <div className="relative pl-6 border-l-2 border-gray-200 space-y-4">
                    {timeline.milestones.map((ms, idx) => (
                      <div key={idx} className="relative">
                        <div className={`absolute -left-[25px] w-3 h-3 rounded-full border-2 ${ms.completed ? 'bg-emerald-500 border-emerald-500' : 'bg-white border-gray-300'}`} />
                        <div className="ml-2">
                          <p className={`text-sm font-medium ${ms.completed ? 'text-gray-900' : 'text-gray-600'}`}>{ms.name}</p>
                          <p className="text-xs text-gray-400">{new Date(ms.date).toLocaleDateString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Delay Factors */}
                {timeline.delay_factors.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-gray-700 mb-2">Delay Factors</p>
                    <div className="flex flex-wrap gap-2">
                      {timeline.delay_factors.map((f, idx) => (
                        <span key={idx} className="px-3 py-1 bg-amber-50 text-amber-700 text-xs rounded-full border border-amber-200">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Denial Patterns */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <AlertTriangle size={16} className="text-red-500" />
            <h3 className="font-medium text-gray-800">Denial Patterns</h3>
          </div>
          <div className="p-6">
            {denialLoading ? (
              <div className="text-center py-8"><Loader2 size={20} className="animate-spin text-gray-400 mx-auto" /></div>
            ) : denialData ? (
              <div className="space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="bg-red-50 rounded-xl p-4 border border-red-100">
                    <div className="flex items-center gap-2 mb-1">
                      <DollarSign size={14} className="text-red-500" />
                      <p className="text-xs text-red-600">Total Denied</p>
                    </div>
                    <p className="text-2xl font-semibold text-red-700">${denialData.total_denied.toLocaleString()}</p>
                  </div>
                  <div className="bg-emerald-50 rounded-xl p-4 border border-emerald-100">
                    <div className="flex items-center gap-2 mb-1">
                      <TrendingUp size={14} className="text-emerald-500" />
                      <p className="text-xs text-emerald-600">Recovery Potential</p>
                    </div>
                    <p className="text-2xl font-semibold text-emerald-700">${denialData.recovery_potential.toLocaleString()}</p>
                  </div>
                </div>

                {denialData.patterns.length > 0 && (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-gray-100">
                          <th className="text-left py-3 px-3 font-medium text-gray-500">Payer</th>
                          <th className="text-left py-3 px-3 font-medium text-gray-500">Code</th>
                          <th className="text-left py-3 px-3 font-medium text-gray-500">Count</th>
                          <th className="text-left py-3 px-3 font-medium text-gray-500">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {denialData.patterns.map((p, idx) => (
                          <tr key={idx}>
                            <td className="py-3 px-3 font-medium text-gray-800">{p.payer}</td>
                            <td className="py-3 px-3 text-gray-600 font-mono text-xs">{p.code}</td>
                            <td className="py-3 px-3">
                              <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${p.count >= 5 ? 'bg-red-100 text-red-700' : 'bg-emerald-100 text-emerald-700'}`}>
                                {p.count}
                              </span>
                            </td>
                            <td className="py-3 px-3 text-gray-600 text-xs">{p.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {denialData.recommendations.length > 0 && (
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles size={14} className="text-violet-500" />
                      <p className="text-sm font-medium text-gray-700">AI Recommendations</p>
                    </div>
                    <ul className="space-y-2">
                      {denialData.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                          <div className="w-1.5 h-1.5 rounded-full bg-violet-400 mt-1.5 flex-shrink-0" />
                          {rec}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">No denial data available</p>
            )}
          </div>
        </section>

        {/* Practice Benchmarks */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <BarChart3 size={16} className="text-blue-500" />
            <h3 className="font-medium text-gray-800">Practice Benchmarks</h3>
          </div>
          <div className="p-6">
            {benchmarkLoading ? (
              <div className="text-center py-8"><Loader2 size={20} className="animate-spin text-gray-400 mx-auto" /></div>
            ) : benchmarks.length > 0 ? (
              <div>
                <p className="text-sm text-gray-500 mb-4">Average treatment duration by phase</p>
                <div className="space-y-3">
                  {benchmarks.map((b, idx) => {
                    const maxDuration = Math.max(...benchmarks.map(x => x.avg_duration_months))
                    const pct = maxDuration > 0 ? (b.avg_duration_months / maxDuration) * 100 : 0
                    return (
                      <div key={idx}>
                        <div className="flex items-center justify-between mb-1">
                          <p className="text-sm text-gray-700 font-medium">{b.phase}</p>
                          <p className="text-sm text-gray-500">{b.avg_duration_months} mo</p>
                        </div>
                        <div className="w-full h-3 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-blue-400 to-blue-500 rounded-full transition-all"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">No benchmark data available</p>
            )}
          </div>
        </section>
      </div>
    </>
  )
}
