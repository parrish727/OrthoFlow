import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import TreatmentJourney from '../components/TreatmentJourney'
import OralCareReminders from '../components/OralCareReminders'
import VideoRoom from '../components/VideoRoom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Calendar, Clock, MessageSquare, FileText, CheckCircle, Send,
  ChevronRight, LogOut, User, AlertCircle, Loader2, Smile,
  Inbox, CalendarCheck, Home, Video,
} from 'lucide-react'

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
  start_time: string
  end_time: string
  type: string | null
  status: string
}

interface Message {
  id: string
  direction: string
  subject: string | null
  body: string
  is_read: boolean
  created_at: string
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
  const [loading, setLoading] = useState(false)
  const [showVideoRoom, setShowVideoRoom] = useState(false)
  const [videoRoomData, setVideoRoomData] = useState<{ room_name: string; token: string } | null>(null)
  const navigate = useNavigate()

  // ── Patient Auth State ─────────────────────────────────────────────────────
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem('portal_token'))
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  async function handlePatientLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/portal/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: loginEmail, password: loginPassword }),
      })
      if (!res.ok) {
        const data = await res.json()
        setLoginError(data.detail || 'Invalid email or password')
        return
      }
      const data = await res.json()
      localStorage.setItem('portal_token', data.access_token)
      localStorage.setItem('portal_patient_name', data.name)
      setIsAuthenticated(true)
    } catch {
      setLoginError('Unable to connect. Please try again.')
    } finally {
      setLoginLoading(false)
    }
  }

  // Portal API helper — uses portal_token instead of staff token
  const portalRequest = useCallback(async (path: string, options: RequestInit = {}) => {
    const token = localStorage.getItem('portal_token')
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const res = await fetch(`${baseUrl}${path}`, {
      ...options,
      headers: {
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
    })
    if (res.status === 401) {
      localStorage.removeItem('portal_token')
      setIsAuthenticated(false)
    }
    return res
  }, [])

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const res = await portalRequest('/api/v1/portal/dashboard')
      if (res.ok) {
        const data = await res.json()
        setDashboard(data)
      }
    } catch {
      // Network error — will show empty state
    }
    setLoading(false)
  }, [portalRequest])

  const loadAppointments = useCallback(async () => {
    const res = await portalRequest('/api/v1/portal/appointments')
    if (res.ok) {
      const data = await res.json()
      setAppointments(data.appointments || [])
    }
  }, [portalRequest])

  const loadMessages = useCallback(async () => {
    const res = await portalRequest('/api/v1/portal/messages')
    if (res.ok) {
      const data = await res.json()
      setMessages(data.messages || [])
    }
  }, [portalRequest])

  const loadForms = useCallback(async () => {
    const res = await portalRequest('/api/v1/portal/forms')
    if (res.ok) {
      const data = await res.json()
      setForms(data.forms || [])
    }
  }, [portalRequest])

  const loadProgress = useCallback(async () => {
    const res = await portalRequest('/api/v1/portal/treatment-progress')
    if (res.ok) {
      const data = await res.json()
      setProgress(data)
    }
  }, [portalRequest])

  useEffect(() => {
    if (!isAuthenticated) return
    loadDashboard()
    loadAppointments()
    loadMessages()
    loadForms()
    loadProgress()
  }, [isAuthenticated, loadDashboard, loadAppointments, loadMessages, loadForms, loadProgress])

  async function handleSendMessage() {
    if (!newMessage.subject.trim() || !newMessage.body.trim()) return
    setSendingMessage(true)
    const res = await portalRequest('/api/v1/portal/messages', {
      method: 'POST',
      body: JSON.stringify(newMessage),
    })
    if (res.ok) {
      setComposing(false)
      setNewMessage({ subject: '', body: '' })
      loadMessages()
    }
    setSendingMessage(false)
  }

  async function handleSubmitForm(formId: string) {
    setSubmittingForm(true)
    const res = await portalRequest(`/api/v1/portal/forms/${formId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ responses: formData }),
    })
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

  function getTimeUntilAppointment(dateStr: string, timeStr: string): string {
    const [h, m] = timeStr.split(':')
    const apptDate = new Date(dateStr)
    apptDate.setHours(parseInt(h, 10), parseInt(m, 10))
    const now = new Date()
    const diffMs = apptDate.getTime() - now.getTime()
    if (diffMs < 0) return 'past'
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
    if (diffDays === 0) return `today at ${formatTime(timeStr)}`
    if (diffDays === 1) return 'tomorrow'
    if (diffDays < 7) return `in ${diffDays} days`
    return formatDate(dateStr)
  }

  const tabVariants = {
    initial: { opacity: 0, y: 12 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -8 },
  }

  const itemVariants = {
    initial: { opacity: 0, y: 8 },
    animate: { opacity: 1, y: 0 },
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="w-14 h-14 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <User size={24} className="text-white" />
            </div>
            <h1 className="text-2xl font-semibold text-gray-900">MyOrthoChart</h1>
            <p className="text-sm text-gray-500 mt-1">Patient Portal — Sign in to your account</p>
          </div>
          <form onSubmit={handlePatientLogin} className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-6 space-y-4">
            {loginError && (
              <div className="flex items-center gap-2 px-3 py-2.5 bg-red-50 border border-red-100 rounded-xl">
                <AlertCircle size={14} className="text-red-500 flex-shrink-0" />
                <span className="text-sm text-red-700">{loginError}</span>
              </div>
            )}
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Email</label>
              <input
                type="email"
                value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                placeholder="your.email@example.com"
                className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={e => setLoginPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-300"
                required
              />
            </div>
            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50"
            >
              {loginLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p className="text-center text-xs text-gray-400 mt-4">
            Powered by OrthoFlow Solutions
          </p>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f5f5f7] flex flex-col items-center justify-center gap-3">
        <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center animate-pulse">
          <Smile size={20} className="text-white" />
        </div>
        <Loader2 size={24} className="animate-spin text-blue-500" />
        <p className="text-sm text-gray-400">Loading your portal...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7] pb-20 md:pb-0">
      {/* Patient Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
              <Smile size={18} className="text-white" />
            </div>
            <div>
              <h1 className="text-base sm:text-lg font-semibold text-gray-900 tracking-tight">MyOrthoChart</h1>
              <p className="text-[11px] text-gray-500 hidden sm:block">Patient Portal</p>
            </div>
          </div>
          <button
            onClick={() => { localStorage.removeItem('portal_token'); localStorage.removeItem('portal_patient_name'); setIsAuthenticated(false) }}
            className="flex items-center gap-2 px-3 py-2 min-h-[44px] text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <LogOut size={16} /> <span className="hidden sm:inline">Sign Out</span>
          </button>
        </div>
      </header>

      {/* Tab Navigation — Desktop top, Mobile bottom sticky */}
      <div className="hidden md:block bg-white border-b border-gray-200/50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6">
          <nav className="flex gap-6">
            {[
              { id: 'home' as const, label: 'Home', icon: Home },
              { id: 'messages' as const, label: 'Messages', icon: MessageSquare },
              { id: 'forms' as const, label: 'Forms', icon: FileText },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 py-3 min-h-[44px] text-sm font-medium border-b-2 transition-colors ${
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

      {/* Mobile Bottom Tab Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-gray-200/80 px-2 pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around">
          {[
            { id: 'home' as const, label: 'Home', icon: Home },
            { id: 'messages' as const, label: 'Messages', icon: MessageSquare },
            { id: 'forms' as const, label: 'Forms', icon: FileText },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex flex-col items-center gap-0.5 py-2 px-4 min-h-[52px] min-w-[64px] transition-colors relative ${
                activeTab === tab.id ? 'text-blue-600' : 'text-gray-400'
              }`}
            >
              <tab.icon size={22} />
              <span className="text-[10px] font-medium">{tab.label}</span>
              {tab.id === 'messages' && dashboard && dashboard.unread_messages > 0 && (
                <span className="absolute top-1.5 right-2 w-2 h-2 bg-blue-500 rounded-full" />
              )}
              {tab.id === 'forms' && dashboard && dashboard.pending_forms > 0 && (
                <span className="absolute top-1.5 right-2 w-2 h-2 bg-amber-500 rounded-full" />
              )}
            </button>
          ))}
        </div>
      </nav>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-5 sm:py-8">
        <AnimatePresence mode="wait">
        {/* HOME TAB */}
        {activeTab === 'home' && (
          <motion.div
            key="home"
            variants={tabVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.2 }}
            className="space-y-5"
          >
            {/* Welcome */}
            <div>
              <h2 className="text-xl sm:text-2xl font-semibold text-gray-900 mb-1">
                Welcome back, {dashboard?.patient_name?.split(' ')[0] || 'Patient'}
              </h2>
              <div className="flex flex-wrap items-center gap-2 mt-2">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
                  {dashboard?.treatment_phase || 'Active Treatment'}
                </span>
                {appointments.length > 0 && (
                  <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                    <Clock size={11} />
                    Next: {getTimeUntilAppointment(appointments[0].date, appointments[0].start_time)}
                  </span>
                )}
              </div>
            </div>

            {/* Join Virtual Visit — shown when doctor is ready */}
            <motion.div
              variants={itemVariants}
              initial="initial"
              animate="animate"
              transition={{ delay: 0.05 }}
              className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl border border-blue-200/80 shadow-sm p-4 sm:p-5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                      <Video size={18} className="text-blue-600" />
                    </div>
                    <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-white animate-pulse" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 text-sm">Virtual Visit Ready</p>
                    <p className="text-xs text-gray-500 mt-0.5">Your doctor is ready to see you</p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setVideoRoomData({ room_name: 'patient-visit', token: 'demo-patient-token' })
                    setShowVideoRoom(true)
                  }}
                  className="px-4 py-2.5 min-h-[44px] bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-medium transition-colors active:scale-95"
                >
                  Join Now
                </button>
              </div>
            </motion.div>

            {/* Upcoming Appointments */}
            <motion.div
              variants={itemVariants}
              initial="initial"
              animate="animate"
              transition={{ delay: 0.1 }}
              className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden"
            >
              <div className="px-4 sm:px-5 py-3.5 border-b border-gray-100 flex items-center gap-2">
                <Calendar size={16} className="text-gray-400" />
                <h3 className="font-medium text-gray-800 text-sm">Upcoming Appointments</h3>
              </div>
              {appointments.length === 0 ? (
                <div className="px-5 py-10 text-center">
                  <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <CalendarCheck size={24} className="text-blue-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">You're all caught up!</p>
                  <p className="text-xs text-gray-400 mt-1">No upcoming appointments.</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {appointments.slice(0, 3).map((appt, i) => (
                    <motion.div
                      key={appt.id}
                      variants={itemVariants}
                      initial="initial"
                      animate="animate"
                      transition={{ delay: 0.05 * i }}
                      className="px-4 sm:px-5 py-3.5 flex items-center justify-between min-h-[56px]"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-blue-50 rounded-xl flex items-center justify-center flex-shrink-0">
                          <Clock size={16} className="text-blue-500" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-medium text-gray-800 text-sm truncate">{appt.type || 'Appointment'}</p>
                          <p className="text-xs text-gray-500">{appt.status}</p>
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0 ml-3">
                        <p className="text-sm font-medium text-gray-700">{formatDate(appt.date)}</p>
                        <p className="text-xs text-gray-400">{formatTime(appt.start_time)}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Treatment Progress */}
            {progress && (
              <motion.div
                variants={itemVariants}
                initial="initial"
                animate="animate"
                transition={{ delay: 0.2 }}
              >
                <TreatmentJourney
                  currentPhase={progress.phase_label || progress.current_phase}
                  phaseOrder={progress.phase_order}
                  totalPhases={progress.total_phases}
                  completedAppointments={progress.completed_appointments || 0}
                  totalAppointments={progress.total_appointments || 0}
                />
              </motion.div>
            )}

            {/* Quick Links */}
            <motion.div
              variants={itemVariants}
              initial="initial"
              animate="animate"
              transition={{ delay: 0.3 }}
              className="grid grid-cols-2 gap-3"
            >
              <button
                onClick={() => setActiveTab('messages')}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 text-left hover:border-blue-200 active:scale-[0.98] transition-all min-h-[88px]"
              >
                <MessageSquare size={20} className="text-blue-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Messages</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {dashboard?.unread_messages || 0} unread
                </p>
              </button>
              <button
                onClick={() => setActiveTab('forms')}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 text-left hover:border-amber-200 active:scale-[0.98] transition-all min-h-[88px]"
              >
                <FileText size={20} className="text-amber-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Forms</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {dashboard?.pending_forms || 0} pending
                </p>
              </button>
            </motion.div>

            {/* Oral Care Reminders */}
            <motion.div
              variants={itemVariants}
              initial="initial"
              animate="animate"
              transition={{ delay: 0.4 }}
            >
              <OralCareReminders treatmentPhase={dashboard?.treatment_phase} />
            </motion.div>
          </motion.div>
        )}

        {/* MESSAGES TAB */}
        {activeTab === 'messages' && (
          <motion.div
            key="messages"
            variants={tabVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            <div className="flex items-center justify-between">
              <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Messages</h2>
              <button
                onClick={() => setComposing(true)}
                className="inline-flex items-center gap-2 px-4 py-2.5 min-h-[44px] bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-full text-sm font-medium transition-all active:scale-95 shadow-sm"
              >
                <Send size={14} /> New Message
              </button>
            </div>

            {/* Compose */}
            <AnimatePresence>
            {composing && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 sm:p-5">
                  <h3 className="font-medium text-gray-800 text-sm mb-3">New Message to Office</h3>
                  <input
                    type="text"
                    placeholder="Subject"
                    value={newMessage.subject}
                    onChange={e => setNewMessage(prev => ({ ...prev, subject: e.target.value }))}
                    className="w-full px-3 py-2.5 min-h-[44px] border border-gray-200 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400"
                  />
                  <textarea
                    placeholder="Type your message..."
                    value={newMessage.body}
                    onChange={e => setNewMessage(prev => ({ ...prev, body: e.target.value }))}
                    rows={4}
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
                  />
                  <div className="flex gap-2 justify-end">
                    <button
                      onClick={() => { setComposing(false); setNewMessage({ subject: '', body: '' }) }}
                      className="px-4 py-2.5 min-h-[44px] text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSendMessage}
                      disabled={sendingMessage}
                      className="px-4 py-2.5 min-h-[44px] bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50"
                    >
                      {sendingMessage ? 'Sending...' : 'Send'}
                    </button>
                  </div>
                </div>
              </motion.div>
            )}
            </AnimatePresence>

            {/* Message List */}
            <div className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden">
              {messages.length === 0 ? (
                <div className="px-5 py-12 text-center">
                  <div className="w-14 h-14 bg-blue-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <Inbox size={24} className="text-blue-400" />
                  </div>
                  <p className="text-sm font-medium text-gray-600">Your inbox is clear.</p>
                  <p className="text-xs text-gray-400 mt-1">Message us anytime!</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {messages.map((msg, i) => (
                    <motion.div
                      key={msg.id}
                      variants={itemVariants}
                      initial="initial"
                      animate="animate"
                      transition={{ delay: 0.03 * i }}
                      className="px-4 sm:px-5 py-4 min-h-[60px]"
                    >
                      <div className="flex items-start justify-between mb-1">
                        <p className="text-sm font-medium text-gray-800 truncate mr-2">{msg.subject}</p>
                        <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0">
                          {new Date(msg.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500 mb-1">
                        {msg.direction === 'from_patient' ? 'You' : 'Office'}
                      </p>
                      <p className="text-sm text-gray-600 line-clamp-2">{msg.body}</p>
                    </motion.div>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}

        {/* FORMS TAB */}
        {activeTab === 'forms' && (
          <motion.div
            key="forms"
            variants={tabVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            transition={{ duration: 0.2 }}
            className="space-y-4"
          >
            <h2 className="text-lg sm:text-xl font-semibold text-gray-900">Forms</h2>

            <AnimatePresence mode="wait">
            {activeForm ? (
              <motion.div
                key="form-active"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.2 }}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm p-4 sm:p-5"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-800">
                    {forms.find(f => f.id === activeForm)?.name || 'Form'}
                  </h3>
                  <button
                    onClick={() => { setActiveForm(null); setFormData({}) }}
                    className="text-sm text-gray-500 hover:text-gray-700 min-h-[44px] px-2 flex items-center"
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
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-400 resize-none"
                    />
                  </div>
                </div>
                <div className="flex justify-end mt-4">
                  <button
                    onClick={() => handleSubmitForm(activeForm)}
                    disabled={submittingForm}
                    className="px-5 py-2.5 min-h-[44px] bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg text-sm font-medium transition-all disabled:opacity-50 active:scale-95"
                  >
                    {submittingForm ? 'Submitting...' : 'Submit Form'}
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.div
                key="form-list"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="bg-white rounded-2xl border border-gray-200/80 shadow-sm overflow-hidden"
              >
                {forms.length === 0 ? (
                  <div className="px-5 py-12 text-center">
                    <div className="w-14 h-14 bg-emerald-50 rounded-2xl flex items-center justify-center mx-auto mb-3">
                      <CheckCircle size={24} className="text-emerald-400" />
                    </div>
                    <p className="text-sm font-medium text-gray-600">All forms complete ✓</p>
                    <p className="text-xs text-gray-400 mt-1">No pending forms at this time.</p>
                  </div>
                ) : (
                  <div className="divide-y divide-gray-50">
                    {forms.map((form, i) => (
                      <motion.div
                        key={form.id}
                        variants={itemVariants}
                        initial="initial"
                        animate="animate"
                        transition={{ delay: 0.05 * i }}
                        className="px-4 sm:px-5 py-4 flex items-center justify-between min-h-[64px]"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                            form.status === 'completed' ? 'bg-emerald-50' : 'bg-amber-50'
                          }`}>
                            {form.status === 'completed' ? (
                              <CheckCircle size={16} className="text-emerald-500" />
                            ) : (
                              <FileText size={16} className="text-amber-500" />
                            )}
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium text-gray-800 text-sm truncate">{form.name}</p>
                            <p className="text-xs text-gray-500 truncate">{form.description}</p>
                            {form.due_date && (
                              <p className="text-xs text-gray-400 mt-0.5">Due: {formatDate(form.due_date)}</p>
                            )}
                          </div>
                        </div>
                        {form.status !== 'completed' && (
                          <button
                            onClick={() => setActiveForm(form.id)}
                            className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 font-medium min-h-[44px] min-w-[44px] justify-center flex-shrink-0 ml-2"
                          >
                            Fill Out <ChevronRight size={14} />
                          </button>
                        )}
                      </motion.div>
                    ))}
                  </div>
                )}
              </motion.div>
            )}
            </AnimatePresence>
          </motion.div>
        )}
        </AnimatePresence>
      </main>

      {/* Virtual Visit Video Room Modal */}
      {showVideoRoom && videoRoomData && (
        <VideoRoom
          roomName={videoRoomData.room_name}
          token={videoRoomData.token}
          onEnd={() => { setShowVideoRoom(false); setVideoRoomData(null) }}
        />
      )}
    </div>
  )
}
