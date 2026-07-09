import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileText, ChevronDown, ChevronRight, Users, LayoutDashboard, Receipt, BarChart3, Settings, User, LogOut, CalendarDays, BookOpen, Shield, Banknote, Send, Sparkles, Loader2 } from 'lucide-react'
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
  payer_name: string
  amount_billed: number
  amount_paid: number | null
  status: 'draft' | 'submitted' | 'accepted' | 'paid' | 'denied'
  service_date: string
  submitted_date: string | null
  denial_reason: string | null
  denial_code: string | null
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
  const [statusCounts, setStatusCounts] = useState<StatusCounts>({ all: 0, draft: 0, submitted: 0, accepted: 0, paid: 0, denied: 0 })
  const [activeTab, setActiveTab] = useState('all')
  const [loading, setLoading] = useState(true)
  const [expandedClaim, setExpandedClaim] = useState<string | null>(null)
  const [submittingClaim, setSubmittingClaim] = useState<string | null>(null)
  const [reviewingDenial, setReviewingDenial] = useState<string | null>(null)
  const [denialReview, setDenialReview] = useState<Record<string, string>>({})
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  useEffect(() => {
    api.getPractice().then(async res => {
      if (res.ok) { const data = await res.json(); setPracticeName(data.name || 'OrthoFlow'); setPracticeLogo(data.logo_url || '') }
    })
  }, [])

  const loadClaims = useCallback(async () => {
    setLoading(true)
    const params = activeTab !== 'all' ? { status: activeTab } : undefined
    const res = await api.getClaims(params)
    if (res.ok) {
      const data = await res.json()
      setClaims(data.claims || data || [])
      if (data.counts) setStatusCounts(data.counts)
    }
    setLoading(false)
  }, [activeTab])

  useEffect(() => { loadClaims() }, [loadClaims])

  async function handleSubmitClaim(claimId: string) {
    setSubmittingClaim(claimId)
    const res = await api.submitClaim(claimId)
    if (res.ok) {
      loadClaims()
    }
    setSubmittingClaim(null)
  }

  async function handleDenialReview(claimId: string) {
    setReviewingDenial(claimId)
    const res = await api.aiDenialReview({ claim_id: claimId })
    if (res.ok) {
      const data = await res.json()
      setDenialReview(prev => ({ ...prev, [claimId]: data.review || data.recommendation || '' }))
    }
    setReviewingDenial(null)
  }

  function formatCurrency(amount: number): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount)
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {practiceLogo ? (
              <img src={practiceLogo} alt="" className="w-8 h-8 rounded-lg object-contain" />
            ) : (
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <FileText size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Claims</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen(!menuOpen)}
                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Menu <ChevronDown size={14} className={`transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl border border-gray-200 shadow-lg py-2 z-50">
                  <DropdownItem icon={LayoutDashboard} label="Dashboard" description="Overview & upload" onClick={() => { setMenuOpen(false); navigate('/') }} />
                  <DropdownItem icon={CalendarDays} label="Schedule" description="Daily appointment board" onClick={() => { setMenuOpen(false); navigate('/schedule') }} />
                  <DropdownItem icon={Users} label="Patients" description="Patient records" onClick={() => { setMenuOpen(false); navigate('/patients') }} />
                  <DropdownItem icon={BookOpen} label="Ledger" description="Patient financials" onClick={() => { setMenuOpen(false); navigate('/ledger') }} />
                  <DropdownItem icon={Shield} label="Insurance" description="Plans & eligibility" onClick={() => { setMenuOpen(false); navigate('/insurance') }} />
                  <DropdownItem icon={FileText} label="Claims" description="Claims management" onClick={() => { setMenuOpen(false); navigate('/claims') }} />
                  <DropdownItem icon={Banknote} label="Payments" description="Payment posting" onClick={() => { setMenuOpen(false); navigate('/payments') }} />
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Title */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">Claims</h2>
          <p className="text-sm text-gray-500 mt-0.5">Manage insurance claims & track status</p>
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
                  ? 'bg-blue-500 text-white shadow-sm'
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
              {claims.map(claim => (
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
                      <p className="text-xs text-gray-500">{claim.payer_name} • {formatDate(claim.service_date)}</p>
                    </div>
                    <span className="text-sm font-medium text-gray-900">{formatCurrency(claim.amount_billed)}</span>
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
                          <div className="mb-4 p-3 rounded-xl bg-purple-50 border border-purple-100">
                            <div className="flex items-center gap-1.5 mb-1">
                              <Sparkles size={12} className="text-purple-600" />
                              <p className="text-xs font-medium text-purple-700">AI Review</p>
                            </div>
                            <p className="text-sm text-purple-700">{denialReview[claim.id]}</p>
                          </div>
                        )}

                        {/* Actions */}
                        <div className="flex items-center gap-3">
                          {claim.status === 'draft' && (
                            <button
                              onClick={() => handleSubmitClaim(claim.id)}
                              disabled={submittingClaim === claim.id}
                              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50"
                            >
                              {submittingClaim === claim.id ? (
                                <><Loader2 size={12} className="animate-spin" /> Submitting...</>
                              ) : (
                                <><Send size={12} /> Submit Claim</>
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
                                <><Loader2 size={12} className="animate-spin" /> Reviewing...</>
                              ) : (
                                <><Sparkles size={12} /> AI Review Denial</>
                              )}
                            </button>
                          )}
                          {claim.amount_paid !== null && (
                            <span className="text-xs text-gray-500">
                              Paid: {formatCurrency(claim.amount_paid)}
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
      </main>
    </div>
  )
}

function DropdownItem({ icon: Icon, label, description, onClick }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; description: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="w-full px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 transition-colors text-left">
      <Icon size={16} className="text-gray-400 flex-shrink-0" />
      <div>
        <p className="text-sm font-medium text-gray-700">{label}</p>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
    </button>
  )
}
