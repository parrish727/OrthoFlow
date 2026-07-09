import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Calendar, Clock, MessageSquare, FileText, CheckCircle, Send,
  ChevronRight, LogOut, User, AlertCircle, Loader2,
} from 'lucide-react'
import { api } from '../lib/api'

interface PortalDashboard {
  patient_name: string
  treatment_phase: string
  unread_messages: number
  pending_forms: number
  next_appointment: { date: string; time: string; type: string } | null
}

interface Appointment {
  id: string
  date: string
  time: string
  type: string
  provider: string
}

interface Message {
  id: string
  from: string
  subject: string
  body: string
  sent_at: string
  is_from_patient: boolean
}

interface FormItem {
  id: string
  name: string
  description: string
  status: string
  due_date: string | null
}

interface TreatmentProgress {
  current_phase: string
  phase_number: number
  total_phases: number
  estimated_completion: string
  milestones: { name: string; completed: boolean }[]
}

export default function PatientPortal() {
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [forms, setForms] = useState<FormItem[]>([])
  const [progress, setProgress] = useState<TreatmentProgress | null>(null)
  const [activeTab, setActiveTab] = useState<'home' | 'messages' | 'forms'>('home')
  const [composing, setComposing] = useState(false)
  const [newMessage, setNewMessage] = useState({ subject: '', body: '' })
  const [sendingMessage, setSendingMessage] = useState(false)
  const [activeForm, setActiveForm] = useState<string | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [submittingForm, setSubmittingForm] = useState(false)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    const res = await api.portalDashboard()
    if (res.ok) {
      const data = await res.json()
      setDashboard(data)
    }
    setLoading(false)
  }, [])

  const loadAppointments = useCallback(async () => {
    const res = await api.portalAppointments()
    if (res.ok) {
      const data = await res.json()
      setAppointments(data.appointments || [])
    }
  }, [])

  const loadMessages = useCallback(async () => {
    const res = await api.portalMessages()
    if (res.ok) {
      const data = await res.json()
      setMessages(data.messages || [])
    }
  }, [])

  const loadForms = useCallback(async () => {
    const res = await api.portalForms()
    if (res.ok) {
      const data = await res.json()
      setForms(data.forms || [])
    }
  }, [])

  const loadProgress = useCallback(async () => {
    const res = await api.portalTreatmentProgress()
    if (res.ok) {
      const data = await res.json()
      setProgress(data)
    }
  }, [])

  useEffect(() => {
    loadDashboard()
    loadAppointments()
    loadMessages()
    loadForms()
    loadProgress()
  }, [loadDashboard, loadAppointments, loadMessages, loadForms, loadProgress])

  async function handleSendMessage() {
    if (!newMessage.subject.trim() || !newMessage.body.trim()) return
    setSendingMessage(true)
    const res = await api.portalSendMessage(newMessage)
    if (res.ok) {
      setComposing(false)
      setNewMessage({ subject: '', body: '' })
      loadMessages()
    }
    setSendingMessage(false)
  }

  async function handleSubmitForm(formId: string) {
    setSubmittingForm(true)
    const res = await api.portalSubmitForm(formId, formData)
    if (res.ok) {
      setActiveForm(null)
      setFormData({})
      loadForms()
    }
    setSubmittingForm(false)
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
  }

  function formatTime(timeStr: string): string {
    const [h, m] = timeStr.split(':')
    const hour = parseInt(h, 10)
    const ampm = hour >= 12 ? 'PM' : 'AM'
    const display = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
    return `${display}:${m} ${ampm}`
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* Patient Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
              <User size={16} className="text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900 tracking-tight">My Portal</h1>
              <p className="text-xs text-gray-500">OrthoFlow Patient Portal</p>
            </div>
          </div>
          <button
            onClick={() => { localStorage.removeItem('portal_token'); navigate('/login') }}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <LogOut size={14} /> Sign Out
          </button>
        </div>
      </header>

      {/* Tab Navigation */}
      <div className="bg-white border-b border-gray-200/50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <nav className="flex gap-6">
            {[
              { id: 'home' as const, label: 'Home', icon: User },
              { id: 'messages' as const, label: 'Messages', icon: MessageSquare },
              { id: 'forms' as const, label: 'Forms', icon: FileText },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                <tab.icon size={16} />
                {tab.label}
                {tab.id === 'messages' && dashboard && dashboard.unread_messages > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs bg-blue-100 text-blue-600 rounded-full">{dashboard.unread_messages}</span>
                )}
                {tab.id === 'forms' && dashboard && dashboard.pending_forms > 0 && (
                  <span className="ml-1 px-1.5 py-0.5 text-xs bg-amber-100 text-amber-600 rounded-full">{dashboard.pending_forms}</span>
                )}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {/* HOME TAB */}
        {activeTab === 'home' && (
          <div className="space-y-6">
            {/* Welcome */}
            <div>
              <h2 className="text-2xl font-semibold text-gray-900 mb-1">
                Welcome back, {dashboard?.patient_name?.split(' ')[0] || 'Patient'}
              </h2>
              <div className="flex items-center gap-2 mt-2">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  {dashboard?.treatment_phase || 'Active Treatment'}
                </span>
              </div>
            </div>

            {/* Upcoming Appointments */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
                <Calendar size={16} className="text-gray-400" />
                <h3 className="font-medium text-gray-800 text-sm">Upcoming Appointments</h3>
              </div>
              {appointments.length === 0 ? (
                <div className="px-5 py-8 text-center">
                  <Calendar size={24} className="text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No upcoming appointments</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {appointments.slice(0, 3).map(appt => (
                    <div key={appt.id} className="px-5 py-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center">
                          <Clock size={16} className="text-blue-500" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-800 text-sm">{appt.type || 'Appointment'}</p>
                          <p className="text-xs text-gray-500">{appt.provider}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-700">{formatDate(appt.date)}</p>
                        <p className="text-xs text-gray-400">{formatTime(appt.time)}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Treatment Progress */}
            {progress && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
                <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle size={16} className="text-gray-400" />
                    <h3 className="font-medium text-gray-800 text-sm">Treatment Progress</h3>
                  </div>
                  <span className="text-xs text-gray-400">Phase {progress.phase_number} of {progress.total_phases}</span>
                </div>
                <div className="px-5 py-4">
                  {/* Progress bar */}
                  <div className="mb-4">
                    <div className="flex justify-between text-xs text-gray-500 mb-1.5">
                      <span>{progress.current_phase}</span>
                      <span>Est. completion: {formatDate(progress.estimated_completion)}</span>
                    </div>
                    <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-full transition-all"
                        style={{ width: `${(progress.phase_number / progress.total_phases) * 100}%` }}
                      />
                    </div>
                  </div>
                  {/* Milestones */}
                  <div className="space-y-2">
                    {progress.milestones.map((m, i) => (
                      <div key={i} className="flex items-center gap-2">
                        {m.completed ? (
                          <CheckCircle size={14} className="text-emerald-500 flex-shrink-0" />
                        ) : (
                          <div className="w-3.5 h-3.5 border-2 border-gray-300 rounded-full flex-shrink-0" />
                        )}
                        <span className={`text-sm ${m.completed ? 'text-gray-500 line-through' : 'text-gray-700'}`}>{m.name}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Quick Links */}
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setActiveTab('messages')}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 text-left hover:border-blue-200 transition-colors"
              >
                <MessageSquare size={20} className="text-blue-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Messages</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {dashboard?.unread_messages || 0} unread
                </p>
              </button>
              <button
                onClick={() => setActiveTab('forms')}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 text-left hover:border-amber-200 transition-colors"
              >
                <FileText size={20} className="text-amber-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Forms</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {dashboard?.pending_forms || 0} pending
                </p>
              </button>
            </div>
          </div>
        )}

        {/* MESSAGES TAB */}
        {activeTab === 'messages' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Messages</h2>
              <button
                onClick={() => setComposing(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-full text-sm font-medium transition-colors"
              >
                <Send size={14} /> New Message
              </button>
            </div>

            {/* Compose */}
            {composing && (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
                <h3 className="font-medium text-gray-800 text-sm mb-3">New Message to Office</h3>
                <input
                  type="text"
                  placeholder="Subject"
                  value={newMessage.subject}
                  onChange={e => setNewMessage(prev => ({ ...prev, subject: e.target.value }))}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                />
                <textarea
                  placeholder="Type your message..."
                  value={newMessage.body}
                  onChange={e => setNewMessage(prev => ({ ...prev, body: e.target.value }))}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
                />
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => { setComposing(false); setNewMessage({ subject: '', body: '' }) }}
                    className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSendMessage}
                    disabled={sendingMessage}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {sendingMessage ? 'Sending...' : 'Send'}
                  </button>
                </div>
              </div>
            )}

            {/* Message List */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              {messages.length === 0 ? (
                <div className="px-5 py-12 text-center">
                  <MessageSquare size={24} className="text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-500">No messages yet</p>
                  <p className="text-xs text-gray-400 mt-1">Start a conversation with your office</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {messages.map(msg => (
                    <div key={msg.id} className="px-5 py-4">
                      <div className="flex items-start justify-between mb-1">
                        <p className="text-sm font-medium text-gray-800">{msg.subject}</p>
                        <span className="text-xs text-gray-400 whitespace-nowrap ml-4">
                          {new Date(msg.sent_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-1">
                        {msg.is_from_patient ? 'You' : msg.from}
                      </p>
                      <p className="text-sm text-gray-600">{msg.body}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* FORMS TAB */}
        {activeTab === 'forms' && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">Forms</h2>

            {activeForm ? (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-800">
                    {forms.find(f => f.id === activeForm)?.name || 'Form'}
                  </h3>
                  <button
                    onClick={() => { setActiveForm(null); setFormData({}) }}
                    className="text-sm text-gray-500 hover:text-gray-700"
                  >
                    Cancel
                  </button>
                </div>
                <p className="text-sm text-gray-500 mb-4">
                  {forms.find(f => f.id === activeForm)?.description}
                </p>
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Response</label>
                    <textarea
                      value={formData.response || ''}
                      onChange={e => setFormData(prev => ({ ...prev, response: e.target.value }))}
                      rows={6}
                      placeholder="Fill out your response here..."
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end mt-4">
                  <button
                    onClick={() => handleSubmitForm(activeForm)}
                    disabled={submittingForm}
                    className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50"
                  >
                    {submittingForm ? 'Submitting...' : 'Submit Form'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
                {forms.length === 0 ? (
                  <div className="px-5 py-12 text-center">
                    <CheckCircle size={24} className="text-emerald-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-500">All forms completed!</p>
                    <p className="text-xs text-gray-400 mt-1">No pending forms at this time</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {forms.map(form => (
                      <div key={form.id} className="px-5 py-4 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                            form.status === 'completed' ? 'bg-emerald-50' : 'bg-amber-50'
                          }`}>
                            {form.status === 'completed' ? (
                              <CheckCircle size={16} className="text-emerald-500" />
                            ) : (
                              <FileText size={16} className="text-amber-500" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium text-gray-800 text-sm">{form.name}</p>
                            <p className="text-xs text-gray-500">{form.description}</p>
                            {form.due_date && (
                              <p className="text-xs text-gray-400 mt-0.5">Due: {formatDate(form.due_date)}</p>
                            )}
                          </div>
                        </div>
                        {form.status !== 'completed' && (
                          <button
                            onClick={() => setActiveForm(form.id)}
                            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium"
                          >
                            Fill Out <ChevronRight size={14} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
