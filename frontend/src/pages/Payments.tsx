import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Banknote, Plus, Upload, ChevronDown, Users, LayoutDashboard, Receipt, BarChart3, Settings, User, LogOut, CalendarDays, BookOpen, Shield, FileText, Loader2 } from 'lucide-react'
import { api } from '../lib/api'

interface PaymentPosting {
  id: string
  source: 'insurance' | 'patient' | 'other'
  payer_name: string
  check_number: string | null
  total_amount: number
  applied_amount: number
  unapplied_amount: number
  status: 'pending' | 'partial' | 'applied' | 'void'
  received_date: string
  posted_by: string | null
}

interface PaymentStats {
  total_received: number
  total_unapplied: number
  total_postings: number
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pending', color: 'bg-amber-50 text-amber-700 border-amber-200' },
  partial: { label: 'Partial', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  applied: { label: 'Applied', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  void: { label: 'Void', color: 'bg-red-50 text-red-600 border-red-200' },
}

const SOURCE_LABELS: Record<string, string> = {
  insurance: 'Insurance',
  patient: 'Patient',
  other: 'Other',
}

export default function Payments() {
  const [postings, setPostings] = useState<PaymentPosting[]>([])
  const [stats, setStats] = useState<PaymentStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [showNewForm, setShowNewForm] = useState(false)
  const [formLoading, setFormLoading] = useState(false)
  const [eraImporting, setEraImporting] = useState(false)
  const [eraResult, setEraResult] = useState<string | null>(null)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // New payment form state
  const [newSource, setNewSource] = useState<'insurance' | 'patient' | 'other'>('insurance')
  const [newPayer, setNewPayer] = useState('')
  const [newCheckNumber, setNewCheckNumber] = useState('')
  const [newAmount, setNewAmount] = useState('')

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

  const loadPostings = useCallback(async () => {
    setLoading(true)
    const res = await api.getPaymentPostings()
    if (res.ok) {
      const data = await res.json()
      setPostings(data.postings || data || [])
      if (data.stats) setStats(data.stats)
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadPostings() }, [loadPostings])

  async function handleNewPayment(e: React.FormEvent) {
    e.preventDefault()
    if (!newPayer || !newAmount) return
    setFormLoading(true)
    const res = await api.createPaymentPosting({
      source: newSource,
      payer_name: newPayer,
      check_number: newCheckNumber || null,
      total_amount: parseFloat(newAmount),
    })
    if (res.ok) {
      setNewSource('insurance')
      setNewPayer('')
      setNewCheckNumber('')
      setNewAmount('')
      setShowNewForm(false)
      loadPostings()
    }
    setFormLoading(false)
  }

  async function handleEraImport(file: File) {
    setEraImporting(true)
    setEraResult(null)
    const res = await api.importEra(file)
    if (res.ok) {
      const data = await res.json()
      setEraResult(data.message || `Imported ${data.count || 0} payment(s) successfully`)
      loadPostings()
    } else {
      setEraResult('Failed to import ERA file. Please check the format and try again.')
    }
    setEraImporting(false)
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
                <Banknote size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Payments</p>
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Payments</h2>
            <p className="text-sm text-gray-500 mt-0.5">Post payments & import ERAs</p>
          </div>
        </div>

        {/* Summary Stats */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Total Received</p>
              <p className="text-lg font-semibold text-gray-900">{formatCurrency(stats.total_received)}</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Unapplied</p>
              <p className={`text-lg font-semibold ${stats.total_unapplied > 0 ? 'text-amber-600' : 'text-gray-900'}`}>
                {formatCurrency(stats.total_unapplied)}
              </p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Total Postings</p>
              <p className="text-lg font-semibold text-gray-900">{stats.total_postings}</p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => setShowNewForm(!showNewForm)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
          >
            <Plus size={16} /> New Payment
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={eraImporting}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 rounded-full text-sm font-medium transition-colors shadow-sm disabled:opacity-50"
          >
            {eraImporting ? (
              <><Loader2 size={16} className="animate-spin" /> Importing...</>
            ) : (
              <><Upload size={16} /> Import ERA</>
            )}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".835,.edi,.txt"
            className="hidden"
            onChange={e => {
              const file = e.target.files?.[0]
              if (file) handleEraImport(file)
              e.target.value = ''
            }}
          />
        </div>

        {/* ERA Import Result */}
        {eraResult && (
          <div className={`mb-6 p-3 rounded-xl text-sm ${eraResult.includes('Failed') ? 'bg-red-50 text-red-700 border border-red-100' : 'bg-emerald-50 text-emerald-700 border border-emerald-100'}`}>
            {eraResult}
          </div>
        )}

        {/* New Payment Form */}
        {showNewForm && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">New Payment Posting</h3>
            <form onSubmit={handleNewPayment} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <select
                value={newSource}
                onChange={e => setNewSource(e.target.value as 'insurance' | 'patient' | 'other')}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="insurance">Insurance</option>
                <option value="patient">Patient</option>
                <option value="other">Other</option>
              </select>
              <input
                type="text"
                placeholder="Payer Name"
                value={newPayer}
                onChange={e => setNewPayer(e.target.value)}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                required
              />
              <input
                type="text"
                placeholder="Check / Reference #"
                value={newCheckNumber}
                onChange={e => setNewCheckNumber(e.target.value)}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
              />
              <input
                type="number"
                step="0.01"
                min="0.01"
                placeholder="Amount ($)"
                value={newAmount}
                onChange={e => setNewAmount(e.target.value)}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                required
              />
              <div className="sm:col-span-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowNewForm(false)}
                  className="px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={formLoading}
                  className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {formLoading ? 'Posting...' : 'Post Payment'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Postings List */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-24" />
                  </div>
                  <div className="w-20 h-4 bg-gray-200 rounded" />
                  <div className="w-20 h-4 bg-gray-100 rounded" />
                  <div className="w-16 h-5 bg-gray-100 rounded-full" />
                </div>
              ))}
            </div>
          ) : postings.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              No payment postings yet
            </div>
          ) : (
            <>
              <div className="hidden sm:grid grid-cols-[1fr_100px_100px_100px_100px_80px] gap-4 px-6 py-3 bg-gray-50 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <span>Payer</span>
                <span>Check #</span>
                <span className="text-right">Total</span>
                <span className="text-right">Applied</span>
                <span className="text-right">Unapplied</span>
                <span className="text-right">Status</span>
              </div>
              <div className="divide-y divide-gray-100">
                {postings.map(posting => (
                  <div key={posting.id} className="grid grid-cols-1 sm:grid-cols-[1fr_100px_100px_100px_100px_80px] gap-2 sm:gap-4 px-6 py-3.5 items-center hover:bg-gray-50/50 transition-colors">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{posting.payer_name}</p>
                      <p className="text-xs text-gray-500">{SOURCE_LABELS[posting.source] || posting.source} • {formatDate(posting.received_date)}</p>
                    </div>
                    <span className="text-sm text-gray-600">{posting.check_number || '—'}</span>
                    <span className="text-sm text-right font-medium text-gray-900">{formatCurrency(posting.total_amount)}</span>
                    <span className="text-sm text-right text-emerald-600">{formatCurrency(posting.applied_amount)}</span>
                    <span className={`text-sm text-right ${posting.unapplied_amount > 0 ? 'text-amber-600 font-medium' : 'text-gray-400'}`}>
                      {formatCurrency(posting.unapplied_amount)}
                    </span>
                    <span className="text-right">
                      <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGES[posting.status]?.color || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                        {STATUS_BADGES[posting.status]?.label || posting.status}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </>
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
