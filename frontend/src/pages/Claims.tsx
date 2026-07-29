import { useState, useEffect, useCallback } from 'react'
import { FileText, ChevronRight, Users, Send, Search, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface ClaimLineItem {
  id: string
  procedure_code: string
  description: string
  amount: number
  units: number
}

interface Claim {
  id: string
  patient_name: string
  payer_id: string
  total_billed: number
  total_paid: number | null
  status: 'draft' | 'submitted' | 'accepted' | 'paid' | 'denied'
  service_date: string
  submission_date: string | null
  denial_reason: string | null
  denial_codes: string[] | null
  line_items: ClaimLineItem[]
}

interface StatusCounts {
  all: number
  draft: number
  submitted: number
  accepted: number
  paid: number
  denied: number
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  draft: { label: 'Draft', color: 'bg-gray-50 text-gray-600 border-gray-200' },
  submitted: { label: 'Submitted', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  accepted: { label: 'Accepted', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  paid: { label: 'Paid', color: 'bg-green-50 text-green-700 border-green-200' },
  denied: { label: 'Denied', color: 'bg-red-50 text-red-600 border-red-200' },
}

const TABS: { key: string; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'draft', label: 'Draft' },
  { key: 'submitted', label: 'Submitted' },
  { key: 'accepted', label: 'Accepted' },
  { key: 'paid', label: 'Paid' },
  { key: 'denied', label: 'Denied' },
]

export default function Claims() {
  const [claims, setClaims] = useState<Claim[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [statusCounts, setStatusCounts] = useState<StatusCounts>({ all: 0, draft: 0, submitted: 0, accepted: 0, paid: 0, denied: 0 })
  const [activeTab, setActiveTab] = useState('all')
  const [loading, setLoading] = useState(true)
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null)
  const [submittingClaim, setSubmittingClaim] = useState<string | null>(null)
  const [reviewingDenial, setReviewingDenial] = useState<string | null>(null)
  const [denialReview, setDenialReview] = useState<Record<string, {
    category: string
    explanation: string
    appeal_recommended: boolean
    success_likelihood: string
    corrective_actions: string[]
    supporting_docs: string[]
  }>>({})
  const [appealLetter, setAppealLetter] = useState<Record<string, string>>({})
  const [generatingAppeal, setGeneratingAppeal] = useState<string | null>(null)
  const loadClaims = useCallback(async () => {
    setLoading(true)
    try {
      const params = activeTab !== 'all' ? { status: activeTab } : undefined
      const res = await api.getClaims(params)
      if (res.ok) {
        const data = await res.json()
        setClaims(data.claims || data || [])
        if (data.counts) setStatusCounts(data.counts)
      }
    } catch {
      // silently handle
    }
    setLoading(false)
  }, [activeTab])

  useEffect(() => { loadClaims() }, [loadClaims])

  async function handleSubmitClaim(claimId: string) {
    setSubmittingClaim(claimId)
    try {
      const res = await api.submitClaim(claimId)
      if (res.ok) {
        loadClaims()
      }
    } catch {
      // silently handle
    }
    setSubmittingClaim(null)
  }

  async function handleDenialReview(claimId: string) {
    setReviewingDenial(claimId)
    try {
      const res = await api.aiDenialReview({ claim_id: claimId })
      if (res.ok) {
        const data = await res.json()
        setDenialReview(prev => ({
          ...prev,
          [claimId]: {
            category: data.denial_category || 'other',
            explanation: data.denial_explanation || '',
            appeal_recommended: data.appeal_recommended ?? false,
            success_likelihood: data.appeal_success_likelihood || 'unknown',
            corrective_actions: data.corrective_actions || [],
            supporting_docs: data.supporting_docs_needed || [],
          },
        }))
      }
    } catch {
      // silently handle
    }
    setReviewingDenial(null)
  }

  async function handleGenerateAppeal(claimId: string) {
    setGeneratingAppeal(claimId)
    try {
      const res = await api.request(`/api/v1/ai/claims/generate-appeal`, {
        method: 'POST',
        body: JSON.stringify({ claim_id: claimId }),
      })
      if (res.ok) {
        const data = await res.json()
        setAppealLetter(prev => ({ ...prev, [claimId]: data.appeal_letter || '' }))
      }
    } catch {
      // silently handle
    }
    setGeneratingAppeal(null)
  }

  function formatCurrency(amount: number | null | undefined): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount || 0)
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <>
        {/* Title + Search */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Claims</h2>
            <p className="text-sm text-gray-500 mt-0.5">Manage insurance claims & track status</p>
          </div>
          <div className="relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by patient or payer..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300 w-64"
            />
          </div>
        </div>

        {/* Status Counts */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mb-6">
          {TABS.map(tab => (
            <div key={tab.key} className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-3 text-center">
              <p className="text-lg font-semibold text-gray-900">{statusCounts[tab.key as keyof StatusCounts] || 0}</p>
              <p className="text-xs text-gray-500">{tab.label}</p>
            </div>
          ))}
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-1 p-1 bg-white rounded-xl border border-gray-200/80 shadow-sm mb-6 overflow-x-auto">
          {TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors whitespace-nowrap ${
                activeTab === tab.key
                  ? 'bg-teal-600 text-white shadow-sm'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Claims List */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3, 4].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-28" />
                  </div>
                  <div className="w-20 h-4 bg-gray-200 rounded" />
                  <div className="w-16 h-5 bg-gray-100 rounded-full" />
                </div>
              ))}
            </div>
          ) : claims.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              {activeTab !== 'all' ? `No ${activeTab} claims` : 'No claims found'}
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {claims.filter(c => {
                if (!searchQuery) return true
                const q = searchQuery.toLowerCase()
                return (c.patient_name || '').toLowerCase().includes(q) || (c.payer_id || '').toLowerCase().includes(q)
              }).map(claim => (
                <div key={claim.id}>
                  <button
                    onClick={() => setExpandedClaim(expandedClaim === claim.id ? null : claim.id)}
                    className="w-full px-6 py-4 flex items-center gap-4 hover:bg-gray-50/50 transition-colors text-left"
                  >
                    <ChevronRight
                      size={16}
                      className={`text-gray-400 transition-transform flex-shrink-0 ${expandedClaim === claim.id ? 'rotate-90' : ''}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">{claim.patient_name}</p>
                      <p className="text-xs text-gray-500">{claim.payer_id} • {formatDate(claim.service_date)}</p>
                    </div>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(claim.total_billed)}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGES[claim.status]?.color || ''}`}>
                      {STATUS_BADGES[claim.status]?.label || claim.status}
                    </span>
                  </button>

                  {/* Expanded Detail */}
                  {expandedClaim === claim.id && (
                    <div className="px-6 pb-5 border-t border-gray-50 bg-gray-50/30">
                      <div className="pt-4">
                        {/* Line Items */}
                        {claim.line_items && claim.line_items.length > 0 && (
                          <div className="mb-4">
                            <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Line Items</h4>
                            <div className="space-y-1.5">
                              {claim.line_items.map(item => (
                                <div key={item.id} className="flex items-center justify-between bg-white rounded-lg px-3 py-2 border border-gray-100">
                                  <div>
                                    <span className="text-xs font-mono text-blue-600 mr-2">{item.procedure_code}</span>
                                    <span className="text-sm text-gray-700">{item.description}</span>
                                  </div>
                                  <span className="text-sm font-medium text-gray-900">
                                    {formatCurrency(item.amount)} × {item.units}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Denial Info */}
                        {claim.status === 'denied' && claim.denial_reason && (
                          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-100">
                            <p className="text-xs font-medium text-red-700 mb-1">
                              Denial Code: {claim.denial_code || 'N/A'}
                            </p>
                            <p className="text-sm text-red-600">{claim.denial_reason}</p>
                          </div>
                        )}

                        {/* AI Denial Review Result */}
                        {denialReview[claim.id] && (
                          <div className="mb-4 space-y-3">
                            <div className="p-4 rounded-xl bg-purple-50 border border-purple-100">
                              <div className="flex items-center justify-between mb-2">
                                <div className="flex items-center gap-1.5">
                                  <Search size={12} className="text-purple-600" />
                                  <p className="text-xs font-semibold text-purple-700 uppercase">AI Denial Analysis</p>
                                </div>
                                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  denialReview[claim.id].appeal_recommended
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {denialReview[claim.id].appeal_recommended ? '✓ APPEAL RECOMMENDED' : 'REVIEW NEEDED'}
                                </span>
                              </div>
                              <p className="text-sm text-purple-800 mb-3">{denialReview[claim.id].explanation.split('\n')[0]}</p>
                              <div className="grid grid-cols-2 gap-3 text-xs">
                                <div>
                                  <p className="font-medium text-gray-600 mb-1">Category</p>
                                  <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full">{denialReview[claim.id].category.replace(/_/g, ' ')}</span>
                                </div>
                                <div>
                                  <p className="font-medium text-gray-600 mb-1">Success Likelihood</p>
                                  <span className={`px-2 py-0.5 rounded-full ${
                                    denialReview[claim.id].success_likelihood === 'high' ? 'bg-green-100 text-green-700' :
                                    denialReview[claim.id].success_likelihood === 'medium' ? 'bg-amber-100 text-amber-700' :
                                    'bg-red-100 text-red-700'
                                  }`}>{denialReview[claim.id].success_likelihood}</span>
                                </div>
                              </div>
                              {denialReview[claim.id].corrective_actions.length > 0 && (
                                <div className="mt-3">
                                  <p className="font-medium text-gray-600 text-xs mb-1">Corrective Actions</p>
                                  <ul className="text-xs text-gray-700 space-y-0.5">
                                    {denialReview[claim.id].corrective_actions.map((a, i) => (
                                      <li key={i} className="flex items-start gap-1.5">
                                        <span className="text-purple-400 mt-0.5">•</span> {a}
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}
                            </div>

                            {/* Generate Appeal Button */}
                            {!appealLetter[claim.id] && (
                              <button
                                onClick={() => handleGenerateAppeal(claim.id)}
                                disabled={generatingAppeal === claim.id}
                                className="w-full py-2.5 bg-gradient-to-r from-teal-600 to-teal-500 hover:from-teal-700 hover:to-teal-600 text-white text-sm font-semibold rounded-xl transition-all disabled:opacity-60 flex items-center justify-center gap-2"
                              >
                                {generatingAppeal === claim.id ? (
                                  <><Loader2 size={14} className="animate-spin" /> Generating Appeal Letter...</>
                                ) : (
                                  <><FileText size={14} /> Generate Appeal Letter</>
                                )}
                              </button>
                            )}

                            {/* Appeal Letter Display */}
                            {appealLetter[claim.id] && (
                              <div className="p-4 rounded-xl bg-teal-50 border border-teal-200">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex items-center gap-1.5">
                                    <FileText size={12} className="text-teal-600" />
                                    <p className="text-xs font-semibold text-teal-700 uppercase">Appeal Letter — Ready to Submit</p>
                                  </div>
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-teal-100 text-teal-700">SAME DAY</span>
                                </div>
                                <pre className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed max-h-[300px] overflow-y-auto">{appealLetter[claim.id]}</pre>
                                <div className="mt-3 flex items-center gap-2">
                                  <button className="flex-1 py-2 bg-teal-600 hover:bg-teal-700 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5">
                                    <Send size={12} /> Submit Appeal to Payer
                                  </button>
                                  <button className="px-3 py-2 bg-white border border-gray-200 text-gray-600 text-xs rounded-lg hover:bg-gray-50 transition-colors">
                                    Edit
                                  </button>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex items-center gap-3">
                          {claim.status === 'draft' && (
                            <button
                              onClick={() => handleSubmitClaim(claim.id)}
                              disabled={submittingClaim === claim.id}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-teal-600 text-white rounded-lg hover:bg-teal-700 transition-colors disabled:opacity-50"
                            >
                              {submittingClaim === claim.id ? (
                                <><Loader2 size={12} className="animate-spin" /> Submitting...    </>
  ) : (
                                <><Send size={12} /> Submit Claim    </>
  )}
                            </button>
                          )}
                          {claim.status === 'denied' && (
                            <button
                              onClick={() => handleDenialReview(claim.id)}
                              disabled={reviewingDenial === claim.id}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors disabled:opacity-50"
                            >
                              {reviewingDenial === claim.id ? (
                                <><Loader2 size={12} className="animate-spin" /> Reviewing...    </>
  ) : (
                                <><Search size={12} /> Review & Appeal    </>
  )}
                            </button>
                          )}
                          {claim.total_paid !== null && (
                            <span className="text-xs text-gray-500">
                              Paid: {formatCurrency(claim.total_paid)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
          </>
  )
}
