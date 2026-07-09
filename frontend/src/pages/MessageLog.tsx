import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessagesSquare, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, MessageSquare, Mail,
  ArrowUpRight, ArrowDownLeft, Search, Filter, Loader2, CheckCircle2,
  XCircle, Clock,
} from 'lucide-react'
import { api } from '../lib/api'

interface MessageEntry {
  id: string
  patient_name: string
  direction: 'outbound' | 'inbound'
  channel: 'sms' | 'email'
  body: string
  body_preview: string
  status: 'queued' | 'sent' | 'delivered' | 'failed' | 'replied'
  created_at: string
  delivered_at: string | null
  replied_at: string | null
  reply_body: string | null
}

interface MessageStats {
  total_sent: number
  delivered_pct: number
  failed: number
  replied: number
  confirmation_rate: number
}

const STATUS_BADGES: Record<string, { label: string; color: string }> = {
  queued: { label: 'Queued', color: 'bg-gray-50 text-gray-600 border-gray-200' },
  sent: { label: 'Sent', color: 'bg-blue-50 text-blue-700 border-blue-200' },
  delivered: { label: 'Delivered', color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  failed: { label: 'Failed', color: 'bg-red-50 text-red-600 border-red-200' },
  replied: { label: 'Replied', color: 'bg-violet-50 text-violet-700 border-violet-200' },
}

export default function MessageLog() {
  const [messages, setMessages] = useState<MessageEntry[]>([])
  const [stats, setStats] = useState<MessageStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterChannel, setFilterChannel] = useState('all')
  const [filterDateFrom, setFilterDateFrom] = useState('')
  const [filterDateTo, setFilterDateTo] = useState('')

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

  const loadMessages = useCallback(async () => {
    setLoading(true)
    const params: Record<string, string> = {}
    if (searchQuery) params.search = searchQuery
    if (filterStatus !== 'all') params.status = filterStatus
    if (filterChannel !== 'all') params.channel = filterChannel
    if (filterDateFrom) params.date_from = filterDateFrom
    if (filterDateTo) params.date_to = filterDateTo

    const [messagesRes, statsRes] = await Promise.all([
      api.getMessageLog(params),
      api.getMessageStats(),
    ])
    if (messagesRes.ok) {
      const data = await messagesRes.json()
      setMessages(data.messages || data || [])
    }
    if (statsRes.ok) {
      const data = await statsRes.json()
      setStats(data)
    }
    setLoading(false)
  }, [searchQuery, filterStatus, filterChannel, filterDateFrom, filterDateTo])

  useEffect(() => { loadMessages() }, [loadMessages])

  function formatTimestamp(dateStr: string): string {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
    })
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
              <div className="w-8 h-8 bg-gradient-to-br from-violet-500 to-violet-600 rounded-lg flex items-center justify-center">
                <MessagesSquare size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Message Log</p>
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
          <h2 className="text-2xl font-semibold text-gray-900">Message Log</h2>
          <p className="text-sm text-gray-500 mt-0.5">Delivery history & tracking</p>
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Total Sent</p>
              <p className="text-lg font-semibold text-gray-900">{stats.total_sent}</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Delivered</p>
              <p className="text-lg font-semibold text-emerald-600">{stats.delivered_pct}%</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Failed</p>
              <p className={`text-lg font-semibold ${stats.failed > 0 ? 'text-red-600' : 'text-gray-900'}`}>{stats.failed}</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Replied</p>
              <p className="text-lg font-semibold text-violet-600">{stats.replied}</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 col-span-2 sm:col-span-1">
              <p className="text-xs text-gray-500 mb-1">Confirmation Rate</p>
              <p className="text-lg font-semibold text-blue-600">{stats.confirmation_rate}%</p>
            </div>
          </div>
        )}

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 mb-6">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search patients..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
              />
            </div>
            <select
              value={filterStatus}
              onChange={e => setFilterStatus(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Status</option>
              <option value="sent">Sent</option>
              <option value="delivered">Delivered</option>
              <option value="failed">Failed</option>
              <option value="replied">Replied</option>
            </select>
            <select
              value={filterChannel}
              onChange={e => setFilterChannel(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              <option value="all">All Channels</option>
              <option value="sms">SMS</option>
              <option value="email">Email</option>
            </select>
            <input
              type="date"
              value={filterDateFrom}
              onChange={e => setFilterDateFrom(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              title="From date"
            />
            <input
              type="date"
              value={filterDateTo}
              onChange={e => setFilterDateTo(e.target.value)}
              className="px-3 py-2 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              title="To date"
            />
          </div>
        </div>

        {/* Message List */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3, 4, 5].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="w-8 h-8 bg-gray-200 rounded-full" />
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-36 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-56" />
                  </div>
                  <div className="w-16 h-5 bg-gray-100 rounded-full" />
                </div>
              ))}
            </div>
          ) : messages.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              No messages found
            </div>
          ) : (
            <>
              {/* Table Header */}
              <div className="hidden sm:grid grid-cols-[80px_1fr_40px_40px_2fr_90px] gap-4 px-6 py-3 bg-gray-50 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
                <span>Time</span>
                <span>Patient</span>
                <span></span>
                <span></span>
                <span>Message</span>
                <span className="text-right">Status</span>
              </div>

              {/* Rows */}
              <div className="divide-y divide-gray-100">
                {messages.map(msg => (
                  <div key={msg.id}>
                    <button
                      onClick={() => setExpandedId(expandedId === msg.id ? null : msg.id)}
                      className="w-full grid grid-cols-1 sm:grid-cols-[80px_1fr_40px_40px_2fr_90px] gap-2 sm:gap-4 px-6 py-3.5 items-center hover:bg-gray-50/50 transition-colors text-left"
                    >
                      <span className="text-xs text-gray-500">{formatTimestamp(msg.created_at)}</span>
                      <span className="text-sm font-medium text-gray-900 truncate">{msg.patient_name}</span>
                      <span>
                        {msg.direction === 'outbound' ? (
                          <ArrowUpRight size={14} className="text-blue-500" />
                        ) : (
                          <ArrowDownLeft size={14} className="text-emerald-500" />
                        )}
                      </span>
                      <span>
                        {msg.channel === 'sms' ? (
                          <MessageSquare size={14} className="text-gray-400" />
                        ) : (
                          <Mail size={14} className="text-gray-400" />
                        )}
                      </span>
                      <span className="text-sm text-gray-600 truncate">{msg.body_preview}</span>
                      <span className="text-right">
                        <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_BADGES[msg.status]?.color || 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                          {STATUS_BADGES[msg.status]?.label || msg.status}
                        </span>
                      </span>
                    </button>

                    {/* Expanded Detail */}
                    {expandedId === msg.id && (
                      <div className="px-6 pb-4 bg-gray-50/30 border-t border-gray-100">
                        <div className="pt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
                          <div>
                            <p className="text-xs text-gray-500 mb-1">Full Message</p>
                            <p className="text-sm text-gray-800 bg-white rounded-xl p-3 border border-gray-100 leading-relaxed">
                              {msg.body}
                            </p>
                          </div>
                          <div className="space-y-3">
                            <div>
                              <p className="text-xs text-gray-500 mb-1">Delivery Timestamps</p>
                              <div className="text-sm text-gray-700 space-y-1">
                                <p className="flex items-center gap-2">
                                  <Clock size={12} className="text-gray-400" />
                                  Created: {formatTimestamp(msg.created_at)}
                                </p>
                                {msg.delivered_at && (
                                  <p className="flex items-center gap-2">
                                    <CheckCircle2 size={12} className="text-emerald-500" />
                                    Delivered: {formatTimestamp(msg.delivered_at)}
                                  </p>
                                )}
                                {msg.status === 'failed' && (
                                  <p className="flex items-center gap-2">
                                    <XCircle size={12} className="text-red-500" />
                                    Failed to deliver
                                  </p>
                                )}
                              </div>
                            </div>
                            {msg.reply_body && (
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Patient Reply</p>
                                <p className="text-sm text-gray-800 bg-violet-50 rounded-xl p-3 border border-violet-100 leading-relaxed">
                                  {msg.reply_body}
                                </p>
                                {msg.replied_at && (
                                  <p className="text-xs text-gray-400 mt-1">{formatTimestamp(msg.replied_at)}</p>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
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
