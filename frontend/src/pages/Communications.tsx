import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare, ChevronDown, Users, LayoutDashboard, CalendarDays, BookOpen,
  Shield, FileText, Banknote, User, LogOut, Plus, Edit3, Eye, Send, X,
  Clock, Mail, Loader2, MessagesSquare, Inbox,
} from 'lucide-react'
import { api } from '../lib/api'

interface Template {
  id: string
  name: string
  channel: 'sms' | 'email'
  body: string
  variables: string[]
  created_at: string
}

interface ScheduledMessage {
  id: string
  patient_name: string
  template_name: string | null
  channel: 'sms' | 'email'
  scheduled_at: string
  body_preview: string
}

interface CommStats {
  sent_today: number
  delivery_rate: number
  pending_queue: number
}

export default function Communications() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [scheduled, setScheduled] = useState<ScheduledMessage[]>([])
  const [stats, setStats] = useState<CommStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)
  const [showSendForm, setShowSendForm] = useState(false)
  const [showNewTemplate, setShowNewTemplate] = useState(false)
  const [sendLoading, setSendLoading] = useState(false)
  const [practiceName, setPracticeName] = useState('OrthoFlow')
  const [practiceLogo, setPracticeLogo] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)
  const navigate = useNavigate()
  const menuRef = useRef<HTMLDivElement>(null)

  // Send form state
  const [sendPatient, setSendPatient] = useState('')
  const [sendTemplate, setSendTemplate] = useState('')
  const [sendChannel, setSendChannel] = useState<'sms' | 'email'>('sms')
  const [sendCustomBody, setSendCustomBody] = useState('')

  // New template form state
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateChannel, setNewTemplateChannel] = useState<'sms' | 'email'>('sms')
  const [newTemplateBody, setNewTemplateBody] = useState('')
  const [templateFormLoading, setTemplateFormLoading] = useState(false)

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
    const [templatesRes, scheduledRes] = await Promise.all([
      api.getTemplates(),
      api.getScheduledMessages(),
    ])
    if (templatesRes.ok) {
      const data = await templatesRes.json()
      setTemplates(data.templates || data || [])
    }
    if (scheduledRes.ok) {
      const data = await scheduledRes.json()
      setScheduled(data.scheduled || data || [])
      if (data.stats) setStats(data.stats)
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault()
    if (!sendPatient) return
    setSendLoading(true)
    const res = await api.sendMessage({
      patient_id: sendPatient,
      template_id: sendTemplate || undefined,
      channel: sendChannel,
      custom_body: sendTemplate ? undefined : sendCustomBody,
    })
    if (res.ok) {
      setSendPatient('')
      setSendTemplate('')
      setSendCustomBody('')
      setShowSendForm(false)
      loadData()
    }
    setSendLoading(false)
  }

  async function handleCreateTemplate(e: React.FormEvent) {
    e.preventDefault()
    if (!newTemplateName || !newTemplateBody) return
    setTemplateFormLoading(true)
    const res = await api.createTemplate({
      name: newTemplateName,
      channel: newTemplateChannel,
      body: newTemplateBody,
    })
    if (res.ok) {
      setNewTemplateName('')
      setNewTemplateChannel('sms')
      setNewTemplateBody('')
      setShowNewTemplate(false)
      loadData()
    }
    setTemplateFormLoading(false)
  }

  async function handleCancelScheduled(id: string) {
    const res = await api.cancelScheduledMessage(id)
    if (res.ok) loadData()
  }

  function formatDateTime(dateStr: string): string {
    return new Date(dateStr).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
  }

  function renderVariableChips(body: string) {
    const parts = body.split(/(\{[^}]+\})/)
    return parts.map((part, i) =>
      part.startsWith('{') && part.endsWith('}') ? (
        <span key={i} className="inline-flex items-center px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 text-xs font-mono mx-0.5">
          {part}
        </span>
      ) : (
        <span key={i}>{part}</span>
      )
    )
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
                <MessageSquare size={16} className="text-white" />
              </div>
            )}
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">{practiceName}</h1>
              <p className="text-xs text-gray-500">Communications</p>
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
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Communications</h2>
            <p className="text-sm text-gray-500 mt-0.5">Templates, sending & scheduling</p>
          </div>
          <button
            onClick={() => setShowSendForm(!showSendForm)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
          >
            <Send size={16} /> Send Message
          </button>
        </div>

        {/* Quick Stats */}
        {stats && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Sent Today</p>
              <p className="text-lg font-semibold text-gray-900">{stats.sent_today}</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Delivery Rate</p>
              <p className="text-lg font-semibold text-emerald-600">{stats.delivery_rate}%</p>
            </div>
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4">
              <p className="text-xs text-gray-500 mb-1">Pending in Queue</p>
              <p className={`text-lg font-semibold ${stats.pending_queue > 0 ? 'text-amber-600' : 'text-gray-900'}`}>
                {stats.pending_queue}
              </p>
            </div>
          </div>
        )}

        {/* Send Message Form */}
        {showSendForm && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Send Message Now</h3>
            <form onSubmit={handleSendMessage} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input
                type="text"
                placeholder="Patient ID or name"
                value={sendPatient}
                onChange={e => setSendPatient(e.target.value)}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                required
              />
              <select
                value={sendChannel}
                onChange={e => setSendChannel(e.target.value as 'sms' | 'email')}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
              >
                <option value="sms">SMS</option>
                <option value="email">Email</option>
              </select>
              <select
                value={sendTemplate}
                onChange={e => setSendTemplate(e.target.value)}
                className="px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 sm:col-span-2"
              >
                <option value="">Custom message (no template)</option>
                {templates.map(t => (
                  <option key={t.id} value={t.id}>{t.name} ({t.channel})</option>
                ))}
              </select>
              {!sendTemplate && (
                <textarea
                  placeholder="Message body..."
                  value={sendCustomBody}
                  onChange={e => setSendCustomBody(e.target.value)}
                  rows={3}
                  className="sm:col-span-2 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 resize-none"
                  required
                />
              )}
              <div className="sm:col-span-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowSendForm(false)}
                  className="px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={sendLoading}
                  className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
                >
                  {sendLoading ? 'Sending...' : 'Send Now'}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Message Templates */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden mb-6">
          <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900">Message Templates</h3>
            <button
              onClick={() => setShowNewTemplate(!showNewTemplate)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
            >
              <Plus size={14} /> New Template
            </button>
          </div>

          {/* New Template Form */}
          {showNewTemplate && (
            <div className="px-6 py-4 border-b border-gray-100 bg-gray-50/50">
              <form onSubmit={handleCreateTemplate} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <input
                  type="text"
                  placeholder="Template name"
                  value={newTemplateName}
                  onChange={e => setNewTemplateName(e.target.value)}
                  className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                  required
                />
                <select
                  value={newTemplateChannel}
                  onChange={e => setNewTemplateChannel(e.target.value as 'sms' | 'email')}
                  className="px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20"
                >
                  <option value="sms">SMS</option>
                  <option value="email">Email</option>
                </select>
                <textarea
                  placeholder="Template body... use {variable_name} for dynamic content"
                  value={newTemplateBody}
                  onChange={e => setNewTemplateBody(e.target.value)}
                  rows={3}
                  className="sm:col-span-2 px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300 resize-none"
                  required
                />
                <div className="sm:col-span-2 flex justify-end gap-3">
                  <button type="button" onClick={() => setShowNewTemplate(false)} className="px-4 py-2.5 text-sm text-gray-600 hover:text-gray-900 transition-colors">
                    Cancel
                  </button>
                  <button type="submit" disabled={templateFormLoading} className="px-5 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
                    {templateFormLoading ? 'Creating...' : 'Create Template'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-40 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-64" />
                  </div>
                  <div className="w-16 h-5 bg-gray-100 rounded-full" />
                </div>
              ))}
            </div>
          ) : templates.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              No templates yet — create one to get started
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {templates.map(template => (
                <div key={template.id} className="px-6 py-3.5 flex items-center gap-4 hover:bg-gray-50/50 transition-colors">
                  <div className="flex-shrink-0">
                    {template.channel === 'sms' ? (
                      <MessageSquare size={16} className="text-blue-500" />
                    ) : (
                      <Mail size={16} className="text-violet-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{template.name}</p>
                    <p className="text-xs text-gray-500 truncate">{template.body}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPreviewTemplate(template)}
                      className="p-1.5 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Preview"
                    >
                      <Eye size={14} />
                    </button>
                    <button
                      className="p-1.5 text-gray-400 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                      title="Edit"
                    >
                      <Edit3 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scheduled Messages */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <Clock size={14} className="text-gray-400" /> Scheduled Messages
            </h3>
          </div>
          {loading ? (
            <div className="p-6 space-y-4">
              {[1, 2, 3].map(i => (
                <div key={i} className="flex items-center gap-4 animate-pulse">
                  <div className="flex-1">
                    <div className="h-4 bg-gray-200 rounded w-36 mb-2" />
                    <div className="h-3 bg-gray-100 rounded w-48" />
                  </div>
                  <div className="w-20 h-4 bg-gray-100 rounded" />
                </div>
              ))}
            </div>
          ) : scheduled.length === 0 ? (
            <div className="py-12 text-center text-gray-400 text-sm">
              No scheduled messages
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {scheduled.map(msg => (
                <div key={msg.id} className="px-6 py-3.5 flex items-center gap-4 hover:bg-gray-50/50 transition-colors">
                  <div className="flex-shrink-0">
                    {msg.channel === 'sms' ? (
                      <MessageSquare size={16} className="text-blue-500" />
                    ) : (
                      <Mail size={16} className="text-violet-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{msg.patient_name}</p>
                    <p className="text-xs text-gray-500 truncate">
                      {msg.template_name ? `Template: ${msg.template_name}` : msg.body_preview}
                    </p>
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatDateTime(msg.scheduled_at)}
                  </span>
                  <button
                    onClick={() => handleCancelScheduled(msg.id)}
                    className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Cancel"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Template Preview Modal */}
      {previewTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setPreviewTemplate(null)}>
          <div className="bg-white rounded-2xl shadow-xl border border-gray-200 max-w-lg w-full mx-4 p-6" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900">Template Preview</h3>
              <button onClick={() => setPreviewTemplate(null)} className="p-1.5 text-gray-400 hover:text-gray-700 rounded-lg transition-colors">
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-xs text-gray-500 mb-1">Name</p>
                <p className="text-sm font-medium text-gray-900">{previewTemplate.name}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Channel</p>
                <span className="inline-flex items-center gap-1.5 text-sm text-gray-700">
                  {previewTemplate.channel === 'sms' ? <MessageSquare size={14} className="text-blue-500" /> : <Mail size={14} className="text-violet-500" />}
                  {previewTemplate.channel.toUpperCase()}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Body</p>
                <div className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-xl p-3 border border-gray-100">
                  {renderVariableChips(previewTemplate.body)}
                </div>
              </div>
              {previewTemplate.variables.length > 0 && (
                <div>
                  <p className="text-xs text-gray-500 mb-1">Variables</p>
                  <div className="flex flex-wrap gap-1.5">
                    {previewTemplate.variables.map(v => (
                      <span key={v} className="px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-xs font-mono border border-blue-100">
                        {`{${v}}`}
                      </span>
                    ))}
                  </div>
                </div>
              )}
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
