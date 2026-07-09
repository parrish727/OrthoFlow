import { useState, useEffect } from 'react'
import { Sparkles, Users, FileText, Loader2, Copy, CheckCircle, ClipboardList, Mail, ImageIcon, Calendar } from 'lucide-react'
import { api } from '../lib/api'

interface Patient {
  id: string
  first_name: string
  last_name: string
}

interface NoteSummary {
  treatment_summary: string
  milestones: string[]
  current_status: string
}

interface ReferralLetter {
  letter: string
  generated_at: string
}

interface ImagingReason {
  alert_type: string
  clinical_guidelines: string
  urgency: string
  recommended_views: string[]
}

interface NextVisitPlan {
  suggested_procedures: string[]
  reasoning: string
  estimated_duration_minutes: number
  supplies_needed: string[]
}

export default function AITools() {
const [patients, setPatients] = useState<Patient[]>([])

  // Note Summarization
  const [summaryPatientId, setSummaryPatientId] = useState('')
  const [summary, setSummary] = useState<NoteSummary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)

  // Referral Letter
  const [referralPatientId, setReferralPatientId] = useState('')
  const [referralTo, setReferralTo] = useState('')
  const [referralSpecialty, setReferralSpecialty] = useState('')
  const [referralAddress, setReferralAddress] = useState('')
  const [referralReason, setReferralReason] = useState('')
  const [referralLetter, setReferralLetter] = useState<ReferralLetter | null>(null)
  const [referralLoading, setReferralLoading] = useState(false)
  const [referralCopied, setReferralCopied] = useState(false)

  // Imaging Reasoning
  const [imagingPatientId, setImagingPatientId] = useState('')
  const [imagingReasons, setImagingReasons] = useState<ImagingReason[]>([])
  const [imagingLoading, setImagingLoading] = useState(false)

  // Next Visit Planner
  const [nextVisitPatientId, setNextVisitPatientId] = useState('')
  const [nextVisitPlan, setNextVisitPlan] = useState<NextVisitPlan | null>(null)
  const [nextVisitLoading, setNextVisitLoading] = useState(false)
useEffect(() => {
    api.getPatients({ page: 1 }).then(async res => {
      if (res.ok) { const data = await res.json(); setPatients(data.patients || data.items || []) }
    })
  }, [])

  async function handleSummarize() {
    if (!summaryPatientId) return
    setSummaryLoading(true)
    const res = await api.aiSummarize(summaryPatientId)
    if (res.ok) {
      const data = await res.json()
      setSummary(data)
    }
    setSummaryLoading(false)
  }

  async function handleGenerateLetter() {
    if (!referralPatientId || !referralTo || !referralReason) return
    setReferralLoading(true)
    const res = await api.aiReferralLetter({
      patient_id: referralPatientId,
      referral_to: { name: referralTo, specialty: referralSpecialty, address: referralAddress },
      reason: referralReason,
    })
    if (res.ok) {
      const data = await res.json()
      setReferralLetter(data)
    }
    setReferralLoading(false)
  }

  async function handleImagingReasoning() {
    if (!imagingPatientId) return
    setImagingLoading(true)
    const res = await api.aiImagingReasoning(imagingPatientId)
    if (res.ok) {
      const data = await res.json()
      setImagingReasons(data.reasons || data.alerts || [])
    }
    setImagingLoading(false)
  }

  async function handleNextVisit() {
    if (!nextVisitPatientId) return
    setNextVisitLoading(true)
    const res = await api.aiNextVisit(nextVisitPatientId)
    if (res.ok) {
      const data = await res.json()
      setNextVisitPlan(data)
    }
    setNextVisitLoading(false)
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text)
    setReferralCopied(true)
    setTimeout(() => setReferralCopied(false), 2000)
  }

  return (
    <>
      <div className="space-y-8">
        {/* Page Title */}
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">AI Tools</h2>
          <p className="text-sm text-gray-500 mt-0.5">AI-powered clinical and administrative tools</p>
        </div>

        {/* Note Summarization */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <ClipboardList size={16} className="text-blue-500" />
            <h3 className="font-medium text-gray-800">Note Summarization</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-500 mb-4">Generate a concise summary of a patient's treatment history</p>
            <div className="flex items-center gap-3 mb-4">
              <select
                value={summaryPatientId}
                onChange={(e) => setSummaryPatientId(e.target.value)}
                className="flex-1 max-w-xs px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-200"
              >
                <option value="">Select patient...</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              <button
                onClick={handleSummarize}
                disabled={summaryLoading || !summaryPatientId}
                className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                {summaryLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                Summarize History
              </button>
            </div>

            {summary && (
              <div className="mt-4 space-y-4 bg-gray-50 rounded-xl p-5 border border-gray-100">
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Treatment Summary</p>
                  <p className="text-sm text-gray-700">{summary.treatment_summary}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Milestones</p>
                  <ul className="space-y-1">
                    {summary.milestones.map((m, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-gray-600">
                        <CheckCircle size={12} className="text-emerald-500 flex-shrink-0" />
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">Current Status</p>
                  <p className="text-sm text-gray-700">{summary.current_status}</p>
                </div>
              </div>
            )}
          </div>
        </section>

        {/* Referral Letter Generator */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <Mail size={16} className="text-violet-500" />
            <h3 className="font-medium text-gray-800">Referral Letter Generator</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-500 mb-4">Generate a professional referral letter with AI</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
              <select
                value={referralPatientId}
                onChange={(e) => setReferralPatientId(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-200"
              >
                <option value="">Select patient...</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Referral to (name)"
                value={referralTo}
                onChange={(e) => setReferralTo(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-200"
              />
              <input
                type="text"
                placeholder="Specialty"
                value={referralSpecialty}
                onChange={(e) => setReferralSpecialty(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-200"
              />
              <input
                type="text"
                placeholder="Address"
                value={referralAddress}
                onChange={(e) => setReferralAddress(e.target.value)}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-200"
              />
            </div>
            <textarea
              placeholder="Reason for referral..."
              value={referralReason}
              onChange={(e) => setReferralReason(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-violet-200 resize-none mb-4"
            />
            <button
              onClick={handleGenerateLetter}
              disabled={referralLoading || !referralPatientId || !referralTo || !referralReason}
              className="flex items-center gap-2 px-4 py-2 bg-violet-500 hover:bg-violet-600 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
            >
              {referralLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
              Generate Letter
            </button>

            {referralLetter && (
              <div className="mt-4 relative">
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans">{referralLetter.letter}</pre>
                </div>
                <button
                  onClick={() => copyToClipboard(referralLetter.letter)}
                  className="absolute top-3 right-3 flex items-center gap-1.5 px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-xs font-medium text-gray-600 hover:bg-gray-50 transition-colors shadow-sm"
                >
                  {referralCopied ? <CheckCircle size={12} className="text-emerald-500" /> : <Copy size={12} />}
                  {referralCopied ? 'Copied!' : 'Copy'}
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Imaging Reasoning */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <ImageIcon size={16} className="text-amber-500" />
            <h3 className="font-medium text-gray-800">Imaging Reasoning</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-500 mb-4">Understand why imaging is recommended based on clinical guidelines</p>
            <div className="flex items-center gap-3 mb-4">
              <select
                value={imagingPatientId}
                onChange={(e) => setImagingPatientId(e.target.value)}
                className="flex-1 max-w-xs px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-amber-200"
              >
                <option value="">Select patient...</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              <button
                onClick={handleImagingReasoning}
                disabled={imagingLoading || !imagingPatientId}
                className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                {imagingLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                Explain Why
              </button>
            </div>

            {imagingReasons.length > 0 && (
              <div className="space-y-4 mt-4">
                {imagingReasons.map((reason, idx) => (
                  <div key={idx} className="bg-amber-50 rounded-xl p-5 border border-amber-100">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="px-2 py-0.5 bg-amber-200 text-amber-800 text-xs font-medium rounded-full">{reason.alert_type}</span>
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        reason.urgency === 'high' ? 'bg-red-100 text-red-700' :
                        reason.urgency === 'medium' ? 'bg-amber-100 text-amber-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {reason.urgency} urgency
                      </span>
                    </div>
                    <div className="space-y-3">
                      <div>
                        <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-1">Clinical Guidelines</p>
                        <p className="text-sm text-gray-700">{reason.clinical_guidelines}</p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-amber-700 uppercase tracking-wide mb-1">Recommended Views</p>
                        <div className="flex flex-wrap gap-2">
                          {reason.recommended_views.map((v, i) => (
                            <span key={i} className="px-2.5 py-1 bg-white border border-amber-200 text-amber-700 text-xs rounded-full">{v}</span>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Next Visit Planner */}
        <section className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
            <Calendar size={16} className="text-emerald-500" />
            <h3 className="font-medium text-gray-800">Next Visit Planner</h3>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-500 mb-4">AI-recommended procedures and preparations for the next appointment</p>
            <div className="flex items-center gap-3 mb-4">
              <select
                value={nextVisitPatientId}
                onChange={(e) => setNextVisitPatientId(e.target.value)}
                className="flex-1 max-w-xs px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-200"
              >
                <option value="">Select patient...</option>
                {patients.map(p => (
                  <option key={p.id} value={p.id}>{p.first_name} {p.last_name}</option>
                ))}
              </select>
              <button
                onClick={handleNextVisit}
                disabled={nextVisitLoading || !nextVisitPatientId}
                className="flex items-center gap-2 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:opacity-50 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
              >
                {nextVisitLoading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                Plan Next Visit
              </button>
            </div>

            {nextVisitPlan && (
              <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Suggested Procedures</p>
                  <ul className="space-y-1.5">
                    {nextVisitPlan.suggested_procedures.map((proc, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-gray-700">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                        {proc}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Reasoning</p>
                  <p className="text-sm text-gray-700">{nextVisitPlan.reasoning}</p>
                </div>
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Estimated Duration</p>
                  <p className="text-2xl font-semibold text-gray-900">{nextVisitPlan.estimated_duration_minutes} <span className="text-sm font-normal text-gray-500">minutes</span></p>
                </div>
                <div className="bg-gray-50 rounded-xl p-5 border border-gray-100">
                  <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Supplies Needed</p>
                  <div className="flex flex-wrap gap-2">
                    {nextVisitPlan.supplies_needed.map((s, idx) => (
                      <span key={idx} className="px-2.5 py-1 bg-white border border-gray-200 text-gray-600 text-xs rounded-full">{s}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </>
  )
}
