import { useState, useEffect, useCallback, useRef } from 'react'
import { MessageSquare, Users, FileText, Plus, Edit3, Eye, Send, X, Clock, Mail, Loader2, Inbox } from 'lucide-react'
import { api } from '../lib/api'

interface PatientResult {
  id: string
  first_name: string
  last_name: string
  phone: string | null
  email: string | null
}

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

interface SentMessage {
  id: string
  patient_id: string
  direction: string
  channel: string
  to_address: string
  body: string
  status: string
  created_at: string
}

export default function Communications() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [scheduled, setScheduled] = useState<ScheduledMessage[]>([])
  const [stats, setStats] = useState<CommStats | null>(null)
  const [recentMessages, setRecentMessages] = useState<SentMessage[]>([])
  const [loading, setLoading] = useState(true)
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)
  const [showSendForm, setShowSendForm] = useState(false)
  const [showNewTemplate, setShowNewTemplate] = useState(false)
  const [sendLoading, setSendLoading] = useState(false)
// Send form state
  const [sendPatient, setSendPatient] = useState('')
  const [sendTemplate, setSendTemplate] = useState('')
  const [sendChannel, setSendChannel] = useState<'sms' | 'email'>('sms')
  const [sendCustomBody, setSendCustomBody] = useState('')

  // Patient search state
  const [patientSearch, setPatientSearch] = useState('')
  const [patientResults, setPatientResults] = useState<PatientResult[]>([])
  const [selectedPatientInfo, setSelectedPatientInfo] = useState<PatientResult | null>(null)
  const [showPatientDropdown, setShowPatientDropdown] = useState(false)
  const patientSearchRef = useRef<HTMLDivElement>(null)

  // New template form state
  const [newTemplateName, setNewTemplateName] = useState('')
  const [newTemplateChannel, setNewTemplateChannel] = useState<'sms' | 'email'>('sms')
  const [newTemplateBody, setNewTemplateBody] = useState('')
  const [templateFormLoading, setTemplateFormLoading] = useState(false)
  const loadData = useCallback(async () => {
    setLoading(true)
    const [templatesRes, scheduledRes, messagesRes] = await Promise.all([
      api.getTemplates(),
      api.getScheduledMessages(),
      api.request('/api/v1/communications/messages/?size=20'),
    ])
    if (templatesRes.ok) {
      const data = await templatesRes.json()
      setTemplates(data.templates || data || [])
    }
    if (scheduledRes.ok) {
      const data = await scheduledRes.json()
      setScheduled(data.scheduled_messages || data.scheduled || data || [])
      if (data.stats) setStats(data.stats)
    }
    if (messagesRes.ok) {
      const data = await messagesRes.json()
      setRecentMessages(data.messages || data || [])
      // Build stats from messages if not provided
      if (!stats) {
        const msgs = data.messages || data || []
        const today = new Date().toDateString()
        const sentToday = msgs.filter((m: SentMessage) => new Date(m.created_at).toDateString() === today && m.direction === 'outbound').length
        const delivered = msgs.filter((m: SentMessage) => m.status === 'delivered').length
        const total = msgs.filter((m: SentMessage) => m.direction === 'outbound').length
        setStats({
          sent_today: sentToday,
          delivery_rate: total > 0 ? Math.round((delivered / total) * 100) : 100,
          pending_queue: msgs.filter((m: SentMessage) => m.status === 'queued' || m.status === 'pending').length,
        })
      }
    }
    setLoading(false)
  }, [])

  useEffect(() => { loadData() }, [loadData])

  // Patient search debounce
  useEffect(() => {
    if (!patientSearch || patientSearch.length < 2) { setPatientResults([]); return }
    const timer = setTimeout(async () => {
      const res = await api.getPatients({ search: patientSearch })
      if (res.ok) {
        const data = await res.json()
        setPatientResults(data.patients || data || [])
        setShowPatientDropdown(true)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [patientSearch])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (patientSearchRef.current && !patientSearchRef.current.contains(e.target as Node)) {
        setShowPatientDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  // Auto-swap contact info when channel changes
  useEffect(() => {
    if (!selectedPatientInfo) return
    // No need to update sendPatient (it's the ID), just let the UI show the right contact
  }, [sendChannel, selectedPatientInfo])

  function handleSelectPatient(patient: PatientResult) {
    setSelectedPatientInfo(patient)
    setSendPatient(patient.id)
    setPatientSearch(`${patient.first_name} ${patient.last_name}`)
    setShowPatientDropdown(false)
    setPatientResults([])
  }

  function getResolvedContact(): string | null {
    if (!selectedPatientInfo) return null
    if (sendChannel === 'sms') return selectedPatientInfo.phone || null
    return selectedPatientInfo.email || null
  }

  async function handleSendMessage(e: React.FormEvent) {
    e.preventDefault()
    if (!sendPatient) return
    setSendLoading(true)
    const res = await api.sendMessage({
      patient_id: sendPatient,
      template_id: sendTemplate || undefined,
      channel: sendChannel,
      body: sendTemplate ? undefined : sendCustomBody,
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
    <>
        {/* Title */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">Communications</h2>
            <p className="text-sm text-gray-500 mt-0.5">Send appointment reminders and messages to patients via email</p>
            <p className="text-sm text-gray-500 mt-0.5">Templates, sending & scheduling</p>
          </div>
          <button
            onClick={() => setShowSendForm(!showSendForm)}
            className="flex items-center gap-2 px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-full text-sm font-medium transition-colors shadow-sm"
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

        {/* Recent Messages — Conversation Log */}
        <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm mb-6 overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <MessageSquare size={16} className="text-teal-600" />
              Recent Messages
            </h3>
            <span className="text-xs text-gray-400">{recentMessages.length} messages</span>
          </div>
          {recentMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Inbox size={32} className="mb-2 opacity-50" />
              <p className="text-sm font-medium">No messages yet</p>
              <p className="text-xs mt-1">Send your first message to a patient above</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50 max-h-[400px] overflow-y-auto">
              {recentMessages.map(msg => (
                <div key={msg.id} className="px-5 py-3 hover:bg-gray-50/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${
                      msg.direction === 'inbound' ? 'bg-blue-100 text-blue-700' : 'bg-teal-100 text-teal-700'
                    }`}>
                      {msg.direction === 'inbound' ? '←' : '→'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-gray-900 truncate">{msg.to_address}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                          msg.channel === 'sms' ? 'bg-violet-100 text-violet-700' : 'bg-blue-100 text-blue-700'
                        }`}>{msg.channel.toUpperCase()}</span>
                        <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                          msg.status === 'delivered' ? 'bg-green-100 text-green-700' :
                          msg.status === 'received' ? 'bg-blue-100 text-blue-700' :
                          msg.status === 'sent' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{msg.status}</span>
                      </div>
                      <p className="text-xs text-gray-600 mt-0.5 truncate">{msg.body}</p>
                    </div>
                    <span className="text-[10px] text-gray-400 whitespace-nowrap">{formatDateTime(msg.created_at)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Send Message Form */}
        {showSendForm && (
          <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5 mb-6">
            <h3 className="text-sm font-semibold text-gray-900 mb-4">Send Message Now</h3>
            <form onSubmit={handleSendMessage} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="relative" ref={patientSearchRef}>
                <input
                  type="text"
                  placeholder="Search patient by name..."
                  value={patientSearch}
                  onChange={e => {
                    setPatientSearch(e.target.value)
                    if (selectedPatientInfo) {
                      setSelectedPatientInfo(null)
                      setSendPatient('')
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                  required
                />
                {showPatientDropdown && patientResults.length > 0 && (
                  <div className="absolute z-20 top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-xl shadow-lg max-h-48 overflow-y-auto">
                    {patientResults.map(p => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => handleSelectPatient(p)}
                        className="w-full text-left px-4 py-2.5 text-sm hover:bg-gray-50 transition-colors flex items-center justify-between"
                      >
                        <span className="font-medium text-gray-900">{p.first_name} {p.last_name}</span>
                        <span className="text-xs text-gray-400">{p.phone || p.email || ''}</span>
                      </button>
                    ))}
                  </div>
                )}
                {selectedPatientInfo && getResolvedContact() && (
                  <p className="text-xs text-teal-600 mt-1">Sending to: {getResolvedContact()}</p>
                )}
                {selectedPatientInfo && !getResolvedContact() && (
                  <p className="text-xs text-amber-600 mt-1">No {sendChannel === 'sms' ? 'phone' : 'email'} on file</p>
                )}
              </div>
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
                  className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
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
                  <button type="submit" disabled={templateFormLoading} className="px-5 py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
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
    </>
  )
}
