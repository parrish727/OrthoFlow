import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  UserCog, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, MessageSquare, MessagesSquare,
  Camera, Bell, Sparkles, Wrench, BarChart3, ArrowUpRight, Search,
  Mail, Clock, CheckCircle, XCircle, Send, X, Link2, Loader2,
} from 'lucide-react'
import { api } from '../lib/api'

interface PortalAccount {
  id: string
  patient_name: string
  email: string
  status: string
  last_login: string | null
}

interface UnreadMessage {
  id: string
  patient_id: string
  patient_name: string
  subject: string
  preview: string
  sent_at: string
}

interface FormSubmission {
  id: string
  patient_name: string
  form_name: string
  submitted_at: string
  status: string
}

export default function PortalAdmin() {
  const [accounts, setAccounts] = useState<PortalAccount[]>([])
  const [messages, setMessages] = useState<UnreadMessage[]>([])
  const [submissions, setSubmissions] = useState<FormSubmission[]>([])
  const [loading, setLoading] = useState(true)
  const [showInviteModal, setShowInviteModal] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [inviteSearch, setInviteSearch] = useState('')
  const [inviting, setInviting] = useState(false)
  const [inviteLink, setInviteLink] = useState<string | null>(null)
  const [replyTo, setReplyTo] = useState<UnreadMessage | null>(null)
  const [replyBody, setReplyBody] = useState('')
  const [sendingReply, setSendingReply] = useState(false)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

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

  const loadData = useCallback(async () => {
    setLoading(true)
    const [accRes, msgRes, subRes] = await Promise.all([
      api.portalAdminAccounts(),
      api.portalAdminMessages(),
      api.portalAdminSubmissions(),
    ])
    if (accRes.ok) { const d = await accRes.json(); setAccounts(d.accounts || []) }
    if (msgRes.ok) { const d = await msgRes.json(); setMessages(d.messages || []) }
    if (subRes.ok) { const d = await subRes.json(); setSubmissions(d.submissions || []) }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  async function handleInvite(patientId: string) {
    setInviting(true)
    const res = await api.portalAdminInvite(patientId)
    if (res.ok) {
      const data = await res.json()
      setInviteLink(data.invite_link || 'Link generated')
      loadData()
    }
    setInviting(false)
  }

  async function handleReply() {
    if (!replyTo || !replyBody.trim()) return
    setSendingReply(true)
    const res = await api.portalAdminReply(replyTo.patient_id, { body: replyBody, subject: `Re: ${replyTo.subject}` })
    if (res.ok) {
      setReplyTo(null)
      setReplyBody('')
      loadData()
    }
    setSendingReply(false)
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }

  const filteredAccounts = accounts.filter(a =>
    a.patient_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    a.email.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
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
              <p className="text-xs text-gray-500">Portal Administration</p>
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
                  <DropdownItem icon={MessageSquare} label="Communications" description="Templates & send" onClick={() => { setMenuOpen(false); navigate('/communications') }} />
                  <DropdownItem icon={MessagesSquare} label="Messages" description="Delivery log" onClick={() => { setMenuOpen(false); navigate('/messages') }} />
                  <DropdownItem icon={Camera} label="Imaging" description="Patient images" onClick={() => { setMenuOpen(false); navigate('/imaging') }} />
                  <DropdownItem icon={Bell} label="Imaging Alerts" description="Overdue imaging" onClick={() => { setMenuOpen(false); navigate('/imaging/alerts') }} />
                  <DropdownItem icon={Sparkles} label="AI Insights" description="Intelligence dashboard" onClick={() => { setMenuOpen(false); navigate('/ai-insights') }} />
                  <DropdownItem icon={Wrench} label="AI Tools" description="Referrals & summaries" onClick={() => { setMenuOpen(false); navigate('/ai-tools') }} />
                  <DropdownItem icon={BarChart3} label="Reports" description="Financial reports" onClick={() => { setMenuOpen(false); navigate('/reports') }} />
                  <DropdownItem icon={ArrowUpRight} label="Migration" description="Patient data import" onClick={() => { setMenuOpen(false); navigate('/migration') }} />
                  <DropdownItem icon={UserCog} label="Portal Admin" description="Patient portal mgmt" onClick={() => { setMenuOpen(false); navigate('/portal-admin') }} />
                  <div className="border-t border-gray-100 my-2" />
                  <DropdownItem icon={User} label="Account" description="Profile & team" onClick={() => { setMenuOpen(false); navigate('/account') }} />
                  <DropdownItem icon={LogOut} label="Sign Out" description="" onClick={() => { localStorage.clear(); navigate('/login') }} />
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* Portal Accounts */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Portal Accounts</h2>
            <button
              onClick={() => { setShowInviteModal(true); setInviteLink(null) }}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <Mail size={14} /> Invite Patient
            </button>
          </div>

          {/* Search */}
          <div className="relative mb-4">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search accounts..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
            />
          </div>

          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50/50">
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Patient</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Last Login</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filteredAccounts.map(acc => (
                    <tr key={acc.id} className="hover:bg-gray-50/50">
                      <td className="px-6 py-3 font-medium text-gray-700">{acc.patient_name}</td>
                      <td className="px-6 py-3 text-gray-600">{acc.email}</td>
                      <td className="px-6 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          acc.status === 'active' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                          acc.status === 'invited' ? 'bg-blue-50 text-blue-700 border border-blue-200' :
                          'bg-gray-50 text-gray-600 border border-gray-200'
                        }`}>
                          {acc.status === 'active' && <CheckCircle size={10} />}
                          {acc.status === 'invited' && <Clock size={10} />}
                          {acc.status === 'inactive' && <XCircle size={10} />}
                          {acc.status}
                        </span>
                      </td>
                      <td className="px-6 py-3 text-gray-500 text-xs">
                        {acc.last_login ? formatDate(acc.last_login) : '—'}
                      </td>
                      <td className="px-6 py-3 text-right">
                        {acc.status === 'active' ? (
                          <button className="text-xs text-red-600 hover:text-red-700 font-medium">Deactivate</button>
                        ) : acc.status === 'inactive' ? (
                          <button
                            onClick={() => handleInvite(acc.id)}
                            className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                          >
                            Re-invite
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredAccounts.length === 0 && (
              <div className="px-6 py-8 text-center text-sm text-gray-500">No accounts found</div>
            )}
          </div>
        </div>

        {/* Two-column layout for messages and submissions */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Unread Messages */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <MessageSquare size={16} className="text-gray-400" />
              <h3 className="font-medium text-gray-800 text-sm">Unread Messages</h3>
              {messages.length > 0 && (
                <span className="ml-auto px-2 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">{messages.length}</span>
              )}
            </div>
            {messages.length === 0 ? (
              <div className="px-6 py-8 text-center">
                <MessageSquare size={20} className="text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No unread messages</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 max-h-80 overflow-y-auto">
                {messages.map(msg => (
                  <div key={msg.id} className="px-5 py-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-800 truncate">{msg.patient_name}</p>
                        <p className="text-xs text-gray-600 mt-0.5">{msg.subject}</p>
                        <p className="text-xs text-gray-400 mt-0.5 truncate">{msg.preview}</p>
                      </div>
                      <button
                        onClick={() => { setReplyTo(msg); setReplyBody('') }}
                        className="ml-3 text-xs text-blue-600 hover:text-blue-700 font-medium whitespace-nowrap"
                      >
                        Reply
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Form Submissions */}
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <FileText size={16} className="text-gray-400" />
              <h3 className="font-medium text-gray-800 text-sm">Form Submissions</h3>
              {submissions.length > 0 && (
                <span className="ml-auto px-2 py-0.5 text-xs bg-amber-100 text-amber-600 rounded-full">{submissions.length}</span>
              )}
            </div>
            {submissions.length === 0 ? (
              <div className="px-6 py-8 text-center">
                <FileText size={20} className="text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No pending submissions</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 max-h-80 overflow-y-auto">
                {submissions.map(sub => (
                  <div key={sub.id} className="px-5 py-3 flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800">{sub.patient_name}</p>
                      <p className="text-xs text-gray-500">{sub.form_name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{formatDate(sub.submitted_at)}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                        sub.status === 'pending' ? 'bg-amber-50 text-amber-700 border border-amber-200' :
                        sub.status === 'reviewed' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' :
                        'bg-gray-50 text-gray-600 border border-gray-200'
                      }`}>
                        {sub.status}
                      </span>
                      <button className="text-xs text-blue-600 hover:text-blue-700 font-medium">Review</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>

      {/* Invite Patient Modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Invite Patient to Portal</h3>
              <button onClick={() => setShowInviteModal(false)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>

            {inviteLink ? (
              <div className="text-center py-4">
                <CheckCircle size={32} className="text-emerald-500 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-800 mb-2">Invitation Sent!</p>
                <div className="flex items-center gap-2 p-3 bg-gray-50 rounded-lg">
                  <Link2 size={14} className="text-gray-400" />
                  <span className="text-xs text-gray-600 truncate flex-1">{inviteLink}</span>
                </div>
                <button
                  onClick={() => setShowInviteModal(false)}
                  className="mt-4 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Done
                </button>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Search Patient</label>
                <div className="relative mb-4">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Type patient name..."
                    value={inviteSearch}
                    onChange={e => setInviteSearch(e.target.value)}
                    className="w-full pl-8 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                  />
                </div>

                {inviteSearch.length >= 2 && (
                  <div className="border border-gray-200 rounded-lg max-h-48 overflow-y-auto mb-4">
                    {accounts
                      .filter(a => a.patient_name.toLowerCase().includes(inviteSearch.toLowerCase()) && a.status !== 'active')
                      .map(a => (
                        <button
                          key={a.id}
                          onClick={() => handleInvite(a.id)}
                          disabled={inviting}
                          className="w-full px-4 py-2.5 text-left hover:bg-gray-50 flex items-center justify-between text-sm border-b border-gray-50 last:border-0"
                        >
                          <span className="text-gray-700">{a.patient_name}</span>
                          <span className="text-xs text-blue-600 font-medium">
                            {inviting ? 'Sending...' : 'Invite'}
                          </span>
                        </button>
                      ))}
                    {accounts.filter(a => a.patient_name.toLowerCase().includes(inviteSearch.toLowerCase()) && a.status !== 'active').length === 0 && (
                      <p className="px-4 py-3 text-xs text-gray-500">No matching patients</p>
                    )}
                  </div>
                )}

                <div className="flex justify-end">
                  <button
                    onClick={() => setShowInviteModal(false)}
                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Reply Modal */}
      {replyTo && (
        <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-gray-900">Reply to {replyTo.patient_name}</h3>
              <button onClick={() => setReplyTo(null)} className="text-gray-400 hover:text-gray-600">
                <X size={20} />
              </button>
            </div>
            <div className="mb-3 p-3 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500 font-medium">{replyTo.subject}</p>
              <p className="text-xs text-gray-400 mt-1">{replyTo.preview}</p>
            </div>
            <textarea
              value={replyBody}
              onChange={e => setReplyBody(e.target.value)}
              rows={4}
              placeholder="Type your reply..."
              className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-4 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setReplyTo(null)}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleReply}
                disabled={sendingReply || !replyBody.trim()}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
              >
                <Send size={14} /> {sendingReply ? 'Sending...' : 'Send Reply'}
              </button>
            </div>
          </div>
        </div>
      )}
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
