import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import VideoRoom from '../components/VideoRoom'
import FormFieldRenderer from '../components/FormFieldRenderer'
import type { FormField } from '../components/FormFieldRenderer'
import TreatmentJourney from '../components/TreatmentJourney'
import {
  Calendar, Clock, MessageSquare, FileText, CheckCircle, Send,
  ChevronRight, LogOut, User, AlertCircle, Loader2, Home, Video,
  Menu, X, CreditCard, Shield, Settings, HelpCircle, Archive,
  BookmarkCheck, Bell, Phone, Monitor, ChevronLeft, Search,
  MapPin, UserCircle, Inbox, CalendarCheck,
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────

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
  phase_label: string
  phase_order: number
  total_phases: number
  completed_appointments: number
  total_appointments: number
  milestones: { name: string; completed: boolean }[]
}

type PortalSection = 'home' | 'schedule' | 'messages' | 'visits' | 'billing' | 'forms' | 'settings'

// ── Utilities ────────────────────────────────────────────────────────────────

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

// ── Main Component ───────────────────────────────────────────────────────────

export default function PatientPortal() {
  // Auth state
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem('portal_token'))
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  // App state
  const [activeSection, setActiveSection] = useState<PortalSection>('home')
  const [menuOpen, setMenuOpen] = useState(false)
  const [dashboard, setDashboard] = useState<PortalDashboard | null>(null)
  const [appointments, setAppointments] = useState<Appointment[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [forms, setForms] = useState<FormItem[]>([])
  const [progress, setProgress] = useState<TreatmentProgress | null>(null)
  const [loading, setLoading] = useState(false)

  // Video state
  const [showVideoRoom, setShowVideoRoom] = useState(false)
  const [videoRoomData, setVideoRoomData] = useState<{ room_name: string; token: string } | null>(null)
  const [activeVisit, setActiveVisit] = useState<{ visit_id: string; room_name: string; patient_token: string } | null>(null)
  const [visitNotification, setVisitNotification] = useState(false)

  // Form state
  const [activeForm, setActiveForm] = useState<string | null>(null)
  const [formData, setFormData] = useState<Record<string, string>>({})
  const [formFields, setFormFields] = useState<FormField[]>([])
  const [formErrors, setFormErrors] = useState<Record<string, string>>({})
  const [formLoading, setFormLoading] = useState(false)
  const [submittingForm, setSubmittingForm] = useState(false)
  const formContainerRef = useRef<HTMLDivElement>(null)

  // Message compose
  const [composing, setComposing] = useState(false)
  const [newMessage, setNewMessage] = useState({ subject: '', body: '' })
  const [sendingMessage, setSendingMessage] = useState(false)
  const [messageFilter, setMessageFilter] = useState<'all' | 'conversations' | 'appointments' | 'automated'>('all')

  // Schedule appointment
  const [scheduleStep, setScheduleStep] = useState(0)
  const [scheduleReason, setScheduleReason] = useState('')
  const [rescheduleApptId, setRescheduleApptId] = useState<string | null>(null)

  // ── Auth ─────────────────────────────────────────────────────────────────

  async function handlePatientLogin(e: React.FormEvent) {
    e.preventDefault()
    setLoginError('')
    setLoginLoading(true)
    try {
      const res = await portalRequest('/api/v1/portal/login', {
        method: 'POST',
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

  function handleLogout() {
    localStorage.removeItem('portal_token')
    localStorage.removeItem('portal_patient_name')
    setIsAuthenticated(false)
    setLoginEmail('')
    setLoginPassword('')
  }

  // ── API Helper ───────────────────────────────────────────────────────────

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

  // ── Data Loading ─────────────────────────────────────────────────────────

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [dashRes, apptRes, msgRes, formRes, progRes] = await Promise.all([
        portalRequest('/api/v1/portal/dashboard'),
        portalRequest('/api/v1/portal/appointments'),
        portalRequest('/api/v1/portal/messages'),
        portalRequest('/api/v1/portal/forms'),
        portalRequest('/api/v1/portal/treatment-progress'),
      ])
      if (dashRes.ok) setDashboard(await dashRes.json())
      if (apptRes.ok) { const d = await apptRes.json(); setAppointments(d.appointments || []) }
      if (msgRes.ok) { const d = await msgRes.json(); setMessages(d.messages || []) }
      if (formRes.ok) { const d = await formRes.json(); setForms(d.forms || []) }
      if (progRes.ok) setProgress(await progRes.json())
    } catch {}
    setLoading(false)
  }, [portalRequest])

  useEffect(() => { if (isAuthenticated) loadAll() }, [isAuthenticated, loadAll])

  // Load form fields when active
  useEffect(() => {
    if (!activeForm) { setFormFields([]); setFormErrors({}); return }
    let cancelled = false
    async function load() {
      setFormLoading(true)
      try {
        const res = await portalRequest('/api/v1/portal/forms/' + activeForm)
        if (res.ok && !cancelled) setFormFields((await res.json()).fields || [])
      } catch {}
      if (!cancelled) setFormLoading(false)
    }
    load()
    return () => { cancelled = true }
  }, [activeForm, portalRequest])

  // Poll for virtual visits
  useEffect(() => {
    if (!isAuthenticated) return
    let hadVisit = false
    async function check() {
      try {
        const res = await portalRequest('/api/v1/portal/virtual-visits/active')
        if (res.ok) {
          const data = await res.json()
          if (data.has_active && data.visits?.length > 0) {
            if (!hadVisit) { setVisitNotification(true); setTimeout(() => setVisitNotification(false), 5000); hadVisit = true }
            setActiveVisit(data.visits[0])
          } else { hadVisit = false; setActiveVisit(null) }
        }
      } catch {}
    }
    check()
    const interval = setInterval(check, 2000)
    return () => clearInterval(interval)
  }, [isAuthenticated, portalRequest])

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function handleSendMessage() {
    if (!newMessage.body.trim()) return
    setSendingMessage(true)
    const res = await portalRequest('/api/v1/portal/messages', {
      method: 'POST',
      body: JSON.stringify(newMessage),
    })
    if (res.ok) { setComposing(false); setNewMessage({ subject: '', body: '' }); loadAll() }
    setSendingMessage(false)
  }

  function handleFieldChange(name: string, value: string) {
    setFormData(prev => ({ ...prev, [name]: value }))
    if (formErrors[name]) setFormErrors(prev => { const n = { ...prev }; delete n[name]; return n })
  }

  async function handleSubmitForm(formId: string) {
    // Validate required fields
    const errors: Record<string, string> = {}
    for (const f of formFields) {
      if (f.required && f.type !== 'section_header' && f.type !== 'paragraph') {
        if (!formData[f.name]?.trim()) errors[f.name] = 'Required'
      }
    }
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      const el = formContainerRef.current?.querySelector(`[data-field="${Object.keys(errors)[0]}"]`)
      el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      return
    }
    setSubmittingForm(true)
    const res = await portalRequest(`/api/v1/portal/forms/${formId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ responses: formData }),
    })
    if (res.ok) { setActiveForm(null); setFormData({}); setFormFields([]); loadAll() }
    setSubmittingForm(false)
  }

  function navigateTo(section: PortalSection) {
    setActiveSection(section)
    setMenuOpen(false)
  }

  const filteredMessages = messages.filter(m => {
    if (messageFilter === 'all') return true
    if (messageFilter === 'conversations') return m.direction === 'from_patient'
    if (messageFilter === 'appointments') return (m.subject || '').toLowerCase().includes('appointment')
    if (messageFilter === 'automated') return (m.subject || '').toLowerCase().includes('reminder') || (m.subject || '').toLowerCase().includes('welcome')
    return true
  })

  const futureAppts = appointments.filter(a => new Date(a.date) >= new Date())
  const pastAppts = appointments.filter(a => new Date(a.date) < new Date())


  // ── Render: Login ────────────────────────────────────────────────────────

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[#f5f5f7] flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <img src="/brand/mark-teal.svg" alt="MyOrthoChart" className="w-14 h-14 mx-auto mb-4" />
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
              <input type="email" value={loginEmail} onChange={e => setLoginEmail(e.target.value)} placeholder="your.email@example.com" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300" required />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1.5">Password</label>
              <input type="password" value={loginPassword} onChange={e => setLoginPassword(e.target.value)} placeholder="••••••••" className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20 focus:border-teal-300" required />
            </div>
            <button type="submit" disabled={loginLoading} className="w-full py-2.5 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium transition-colors disabled:opacity-50">
              {loginLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p className="text-center text-xs text-gray-400 mt-4">Powered by OrthoFlow Solutions</p>
        </div>
      </div>
    )
  }

  if (loading && !dashboard) {
    return (
      <div className="min-h-screen bg-[#f5f5f7] flex flex-col items-center justify-center gap-3">
        <img src="/brand/mark-teal.svg" alt="" className="w-12 h-12 animate-pulse" />
        <Loader2 size={24} className="animate-spin text-teal-500" />
      </div>
    )
  }

  // ── Render: Main App ─────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-[#f5f5f7] pb-20 md:pb-0">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-xl border-b border-gray-200/50 sticky top-0 z-40">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setMenuOpen(true)} className="p-2 -ml-2 hover:bg-gray-100 rounded-lg" aria-label="Menu">
              <Menu size={20} className="text-gray-700" />
            </button>
            <div>
              <h1 className="text-base font-semibold text-gray-900 tracking-tight">MyOrthoChart</h1>
              <p className="text-[11px] text-gray-500 hidden sm:block">{dashboard?.patient_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {dashboard && dashboard.unread_messages > 0 && (
              <button onClick={() => navigateTo('messages')} className="relative p-2 hover:bg-gray-100 rounded-lg">
                <Bell size={18} className="text-gray-600" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-teal-500 rounded-full" />
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Hamburger Menu Overlay */}
      <AnimatePresence>
        {menuOpen && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 bg-black/30 z-50" onClick={() => setMenuOpen(false)} />
            <motion.div initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ type: 'spring', damping: 25 }} className="fixed left-0 top-0 bottom-0 w-72 bg-white z-50 shadow-xl">
              <div className="p-5 border-b border-gray-100">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-teal-100 rounded-full flex items-center justify-center">
                      <User size={18} className="text-teal-600" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-gray-900">{dashboard?.patient_name}</p>
                      <p className="text-xs text-gray-500">{dashboard?.treatment_phase}</p>
                    </div>
                  </div>
                  <button onClick={() => setMenuOpen(false)} className="p-1 hover:bg-gray-100 rounded"><X size={18} className="text-gray-400" /></button>
                </div>
              </div>
              <nav className="py-2">
                {([
                  { id: 'home' as const, icon: Home, label: 'Home' },
                  { id: 'schedule' as const, icon: Calendar, label: 'Schedule an Appointment' },
                  { id: 'messages' as const, icon: MessageSquare, label: 'Messages', badge: dashboard?.unread_messages },
                  { id: 'visits' as const, icon: CalendarCheck, label: 'Visits' },
                  { id: 'billing' as const, icon: CreditCard, label: 'Billing' },
                  { id: 'forms' as const, icon: FileText, label: 'My Records / Forms', badge: dashboard?.pending_forms },
                ] as const).map(item => (
                  <button key={item.id} onClick={() => navigateTo(item.id)} className={`w-full flex items-center gap-3 px-5 py-3 text-left transition-colors ${activeSection === item.id ? 'bg-teal-50 text-teal-700 border-r-2 border-teal-500' : 'text-gray-700 hover:bg-gray-50'}`}>
                    <item.icon size={18} />
                    <span className="text-sm font-medium">{item.label}</span>
                    {item.badge ? <span className="ml-auto px-2 py-0.5 text-xs bg-teal-100 text-teal-700 rounded-full">{item.badge}</span> : null}
                  </button>
                ))}
                <div className="border-t border-gray-100 mt-2 pt-2">
                  {([
                    { id: 'settings' as const, icon: Settings, label: 'Settings' },
                  ] as const).map(item => (
                    <button key={item.id} onClick={() => navigateTo(item.id)} className="w-full flex items-center gap-3 px-5 py-3 text-left text-gray-600 hover:bg-gray-50">
                      <item.icon size={18} /> <span className="text-sm">{item.label}</span>
                    </button>
                  ))}
                  <button onClick={handleLogout} className="w-full flex items-center gap-3 px-5 py-3 text-left text-red-600 hover:bg-red-50">
                    <LogOut size={18} /> <span className="text-sm font-medium">Sign Out</span>
                  </button>
                </div>
              </nav>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Main Content */}
      <main className="max-w-3xl mx-auto px-4 py-5">

        {/* ═══ HOME ═══ */}
        {activeSection === 'home' && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-gray-900">Welcome, {dashboard?.patient_name?.split(' ')[0]}</h2>

            {/* Virtual Visit Notification */}
            <AnimatePresence>
              {visitNotification && (
                <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="bg-teal-600 text-white rounded-2xl p-4 shadow-lg flex items-center gap-3">
                  <Video size={20} className="animate-pulse" />
                  <div className="flex-1">
                    <p className="font-semibold text-sm">Your doctor is ready!</p>
                    <p className="text-xs text-white/80">A virtual visit has been started.</p>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {activeVisit && (
              <div className="bg-gradient-to-r from-teal-50 to-teal-100 rounded-2xl border border-teal-200 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <Video size={18} className="text-teal-600" />
                    <div>
                      <p className="font-medium text-gray-900 text-sm">Virtual Visit Ready</p>
                      <p className="text-xs text-gray-500">Your doctor will be with you shortly</p>
                    </div>
                  </div>
                  <button onClick={() => { setVideoRoomData({ room_name: activeVisit.room_name, token: activeVisit.patient_token }); setShowVideoRoom(true) }} className="px-4 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-xl text-sm font-medium">
                    Join Visit
                  </button>
                </div>
              </div>
            )}

            {/* Treatment Progress */}
            {progress && (
              <TreatmentJourney currentPhase={progress.phase_label || progress.current_phase} phaseOrder={progress.phase_order} totalPhases={progress.total_phases} completedAppointments={progress.completed_appointments || 0} totalAppointments={progress.total_appointments || 0} />
            )}

            {/* Quick Actions Grid */}
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => navigateTo('schedule')} className="bg-white rounded-2xl border border-gray-200 p-4 text-left hover:border-teal-200 transition-all">
                <Calendar size={20} className="text-teal-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Schedule</p>
                <p className="text-xs text-gray-500 mt-0.5">Book appointment</p>
              </button>
              <button onClick={() => navigateTo('messages')} className="bg-white rounded-2xl border border-gray-200 p-4 text-left hover:border-teal-200 transition-all">
                <MessageSquare size={20} className="text-blue-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Messages</p>
                <p className="text-xs text-gray-500 mt-0.5">{dashboard?.unread_messages || 0} unread</p>
              </button>
              <button onClick={() => navigateTo('visits')} className="bg-white rounded-2xl border border-gray-200 p-4 text-left hover:border-teal-200 transition-all">
                <CalendarCheck size={20} className="text-violet-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Visits</p>
                <p className="text-xs text-gray-500 mt-0.5">{futureAppts.length} upcoming</p>
              </button>
              <button onClick={() => navigateTo('billing')} className="bg-white rounded-2xl border border-gray-200 p-4 text-left hover:border-teal-200 transition-all">
                <CreditCard size={20} className="text-emerald-500 mb-2" />
                <p className="text-sm font-medium text-gray-800">Billing</p>
                <p className="text-xs text-gray-500 mt-0.5">View balance</p>
              </button>
            </div>

            {/* Pending Forms Notification */}
            {dashboard && dashboard.pending_forms > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 flex items-center gap-3">
                <Bell size={18} className="text-amber-600" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-800">Paperwork Required</p>
                  <p className="text-xs text-amber-600">{dashboard.pending_forms} form(s) need your attention</p>
                </div>
                <button onClick={() => navigateTo('forms')} className="px-3 py-1.5 bg-amber-600 text-white text-xs font-medium rounded-lg">Complete</button>
              </div>
            )}

            {/* Next Appointment */}
            {appointments.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200 p-4">
                <p className="text-xs text-gray-500 uppercase font-medium tracking-wide mb-2">Next Appointment</p>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-gray-900">{appointments[0].type || 'Appointment'}</p>
                    <p className="text-xs text-gray-500">{formatDate(appointments[0].date)} at {formatTime(appointments[0].start_time)}</p>
                  </div>
                  <button onClick={() => { setRescheduleApptId(appointments[0].id); navigateTo('schedule') }} className="text-xs text-teal-600 font-medium hover:text-teal-700">Reschedule</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ SCHEDULE AN APPOINTMENT ═══ */}
        {activeSection === 'schedule' && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <button onClick={() => { navigateTo('home'); setScheduleStep(0); setRescheduleApptId(null) }} className="p-1 hover:bg-gray-100 rounded"><ChevronLeft size={20} className="text-gray-500" /></button>
              <h2 className="text-xl font-semibold text-gray-900">{rescheduleApptId ? 'Reschedule Appointment' : 'Schedule an Appointment'}</h2>
            </div>

            <div className="bg-white rounded-2xl border border-gray-200 p-5 space-y-4">
              {scheduleStep === 0 && (
                <>
                  <p className="text-sm text-gray-600">What is the reason for your visit?</p>
                  <div className="space-y-2">
                    {['Adjustment', 'Wire Change', 'Broken Bracket', 'Retainer Check', 'Consultation', 'Aligner Check', 'Other'].map(reason => (
                      <button key={reason} onClick={() => { setScheduleReason(reason); setScheduleStep(1) }} className="w-full text-left px-4 py-3 border border-gray-200 rounded-xl text-sm hover:border-teal-300 hover:bg-teal-50/50 transition-colors flex items-center justify-between">
                        {reason} <ChevronRight size={16} className="text-gray-400" />
                      </button>
                    ))}
                  </div>
                </>
              )}
              {scheduleStep === 1 && (
                <>
                  <p className="text-sm text-gray-600">Select a provider:</p>
                  <div className="space-y-2">
                    {['Dr. Parrish Knowles', 'Dr. Williams'].map(doc => (
                      <button key={doc} onClick={() => setScheduleStep(2)} className="w-full text-left px-4 py-3 border border-gray-200 rounded-xl text-sm hover:border-teal-300 hover:bg-teal-50/50 transition-colors flex items-center gap-3">
                        <UserCircle size={20} className="text-gray-400" /> {doc}
                      </button>
                    ))}
                  </div>
                  <button onClick={() => setScheduleStep(0)} className="text-xs text-gray-500 hover:text-gray-700">← Back</button>
                </>
              )}
              {scheduleStep === 2 && (
                <div className="text-center py-6">
                  <CheckCircle size={32} className="text-teal-500 mx-auto mb-3" />
                  <p className="text-sm font-medium text-gray-900">Request Submitted!</p>
                  <p className="text-xs text-gray-500 mt-1">Your office will confirm your {scheduleReason} appointment shortly.</p>
                  <p className="text-xs text-gray-400 mt-3">You'll receive a notification when it's confirmed.</p>
                  <button onClick={() => { setScheduleStep(0); navigateTo('home') }} className="mt-4 px-4 py-2 bg-teal-600 text-white rounded-xl text-sm font-medium">Done</button>
                </div>
              )}
            </div>
          </div>
        )}


        {/* ═══ MESSAGES ═══ */}
        {activeSection === 'messages' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold text-gray-900">Messages</h2>
              <button onClick={() => setComposing(true)} className="flex items-center gap-2 px-4 py-2 bg-teal-600 text-white rounded-full text-sm font-medium">
                <Send size={14} /> New
              </button>
            </div>
            {/* Filters */}
            <div className="flex gap-2 overflow-x-auto pb-1">
              {([['all', 'All'], ['conversations', 'Conversations'], ['appointments', 'Appointments'], ['automated', 'Automated']] as const).map(([key, label]) => (
                <button key={key} onClick={() => setMessageFilter(key)} className={`px-3 py-1.5 text-xs font-medium rounded-full whitespace-nowrap ${messageFilter === key ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-600'}`}>{label}</button>
              ))}
            </div>
            {/* Compose */}
            {composing && (
              <div className="bg-white rounded-2xl border border-gray-200 p-4 space-y-3">
                <input type="text" placeholder="Subject" value={newMessage.subject} onChange={e => setNewMessage(p => ({ ...p, subject: e.target.value }))} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
                <textarea placeholder="Type your message..." value={newMessage.body} onChange={e => setNewMessage(p => ({ ...p, body: e.target.value }))} rows={4} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm resize-none" />
                <div className="flex gap-2 justify-end">
                  <button onClick={() => setComposing(false)} className="px-3 py-2 text-sm text-gray-600">Cancel</button>
                  <button onClick={handleSendMessage} disabled={sendingMessage} className="px-4 py-2 bg-teal-600 text-white text-sm rounded-lg disabled:opacity-50">{sendingMessage ? 'Sending...' : 'Send'}</button>
                </div>
              </div>
            )}
            {/* Message List */}
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden divide-y divide-gray-50">
              {filteredMessages.length === 0 ? (
                <div className="py-12 text-center"><Inbox size={24} className="text-gray-300 mx-auto mb-2" /><p className="text-sm text-gray-400">No messages</p></div>
              ) : filteredMessages.map(msg => (
                <div key={msg.id} className="px-4 py-3.5">
                  <div className="flex items-start justify-between mb-1">
                    <p className="text-sm font-medium text-gray-800">{msg.subject || '(No subject)'}</p>
                    <span className="text-xs text-gray-400">{new Date(msg.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs text-gray-500 mb-1">{msg.direction === 'from_patient' ? 'You' : 'Office'}</p>
                  <p className="text-sm text-gray-600 line-clamp-2">{msg.body}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═══ VISITS ═══ */}
        {activeSection === 'visits' && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-gray-900">Visits</h2>

            {/* Future Visits */}
            {futureAppts.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 uppercase font-medium tracking-wide mb-2">Upcoming</p>
                <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden divide-y divide-gray-50">
                  {futureAppts.map(appt => {
                    const isVirtual = (appt.type || '').toLowerCase().includes('virtual')
                    const apptDate = new Date(appt.date)
                    const isToday = apptDate.toDateString() === new Date().toDateString()
                    return (
                      <div key={appt.id} className="px-4 py-4">
                        {isToday && <div className="mb-2 px-2 py-1 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700 font-medium inline-block">It's time for your visit!</div>}
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium text-gray-900">{appt.type || 'Appointment'}</p>
                            <p className="text-xs text-gray-500">{formatDate(appt.date)} at {formatTime(appt.start_time)}</p>
                            <p className="text-xs text-gray-400 mt-0.5">{isVirtual ? '📹 Virtual Visit' : '🏥 In-Person'}</p>
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            <button onClick={() => { setRescheduleApptId(appt.id); navigateTo('schedule') }} className="text-xs text-teal-600 font-medium">Reschedule</button>
                            {isVirtual && isToday && <button className="text-xs text-blue-600 font-medium">Join Visit</button>}
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Past Visits */}
            {pastAppts.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 uppercase font-medium tracking-wide mb-2">Past Visits</p>
                <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden divide-y divide-gray-50">
                  {pastAppts.slice(0, 10).map(appt => (
                    <div key={appt.id} className="px-4 py-3 flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-700">{appt.type || 'Visit'}</p>
                        <p className="text-xs text-gray-400">{formatDate(appt.date)}</p>
                      </div>
                      <span className="text-xs text-gray-400 capitalize">{appt.status}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ═══ BILLING ═══ */}
        {activeSection === 'billing' && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-gray-900">Billing</h2>
            <div className="bg-white rounded-2xl border border-gray-200 p-5">
              <div className="text-center mb-5">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Balance Due</p>
                <p className="text-3xl font-bold text-gray-900 mt-1">$2,935.00</p>
                <p className="text-xs text-gray-500 mt-1">Responsible Party: Priscilla Knowles</p>
              </div>
              <div className="space-y-2">
                <button className="w-full flex items-center justify-between px-4 py-3 border border-gray-200 rounded-xl text-sm hover:bg-gray-50">
                  <span className="text-gray-700">View Balance Details</span><ChevronRight size={16} className="text-gray-400" />
                </button>
                <button className="w-full flex items-center justify-between px-4 py-3 border border-gray-200 rounded-xl text-sm hover:bg-gray-50">
                  <span className="text-gray-700">Contact Customer Service</span><ChevronRight size={16} className="text-gray-400" />
                </button>
                <button className="w-full flex items-center justify-between px-4 py-3 border border-gray-200 rounded-xl text-sm hover:bg-gray-50">
                  <span className="text-gray-700">Manage Billing Methods</span><ChevronRight size={16} className="text-gray-400" />
                </button>
              </div>
            </div>
            {/* Insurance Card */}
            <div className="bg-white rounded-2xl border border-gray-200 p-5">
              <div className="flex items-center gap-2 mb-3">
                <Shield size={16} className="text-blue-500" />
                <p className="text-sm font-semibold text-gray-900">Insurance</p>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Plan</span><span className="text-gray-900">Delta Dental PPO Plus</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Subscriber ID</span><span className="text-gray-900 font-mono">DDW-9204150001</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Group</span><span className="text-gray-900">GRP-MELANIN-2026</span></div>
              </div>
            </div>
          </div>
        )}

        {/* ═══ FORMS / MY RECORDS ═══ */}
        {activeSection === 'forms' && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900">My Records</h2>
            {activeForm ? (
              <div className="bg-white rounded-2xl border border-gray-200 p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-800">{forms.find(f => f.id === activeForm)?.name}</h3>
                  <button onClick={() => { setActiveForm(null); setFormData({}); setFormFields([]) }} className="text-sm text-gray-500">Cancel</button>
                </div>
                <div ref={formContainerRef}>
                  {formLoading ? <Loader2 size={20} className="animate-spin text-teal-500 mx-auto" /> : formFields.length > 0 ? (
                    <FormFieldRenderer fields={formFields} values={formData} onChange={handleFieldChange} errors={formErrors} />
                  ) : <p className="text-sm text-gray-400 text-center py-4">No fields configured.</p>}
                </div>
                <div className="flex justify-end mt-4">
                  <button onClick={() => handleSubmitForm(activeForm)} disabled={submittingForm} className="px-5 py-2.5 bg-teal-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
                    {submittingForm ? 'Submitting...' : 'Submit'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden divide-y divide-gray-50">
                {forms.length === 0 ? (
                  <div className="py-12 text-center"><CheckCircle size={24} className="text-emerald-400 mx-auto mb-2" /><p className="text-sm text-gray-500">All forms complete ✓</p></div>
                ) : forms.map(form => (
                  <div key={form.id} className="px-4 py-4 flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-800">{form.name}</p>
                      <p className="text-xs text-gray-500">{form.description}</p>
                    </div>
                    {form.status !== 'completed' ? (
                      <button onClick={() => setActiveForm(form.id)} className="text-sm text-teal-600 font-medium">Fill Out</button>
                    ) : (
                      <CheckCircle size={16} className="text-emerald-500" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ═══ SETTINGS ═══ */}
        {activeSection === 'settings' && (
          <div className="space-y-5">
            <h2 className="text-xl font-semibold text-gray-900">Settings</h2>
            <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden divide-y divide-gray-50">
              <div className="px-4 py-4">
                <p className="text-sm font-medium text-gray-800">Account Information</p>
                <p className="text-xs text-gray-500 mt-0.5">{dashboard?.patient_name}</p>
              </div>
              <div className="px-4 py-4">
                <p className="text-sm font-medium text-gray-800">Notification Preferences</p>
                <p className="text-xs text-gray-500 mt-0.5">Manage email and SMS notifications</p>
              </div>
              <div className="px-4 py-4">
                <p className="text-sm font-medium text-gray-800">Privacy & Security</p>
                <p className="text-xs text-gray-500 mt-0.5">Password, two-factor authentication</p>
              </div>
              <button onClick={handleLogout} className="w-full px-4 py-4 text-left">
                <p className="text-sm font-medium text-red-600">Sign Out</p>
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Bottom Navigation (Mobile) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 bg-white/90 backdrop-blur-xl border-t border-gray-200/80 px-2 pb-[env(safe-area-inset-bottom)]">
        <div className="flex justify-around">
          {([
            { id: 'home' as const, icon: Home, label: 'Home' },
            { id: 'messages' as const, icon: MessageSquare, label: 'Messages' },
            { id: 'visits' as const, icon: CalendarCheck, label: 'Visits' },
            { id: 'billing' as const, icon: CreditCard, label: 'Billing' },
          ] as const).map(tab => (
            <button key={tab.id} onClick={() => setActiveSection(tab.id)} className={`flex flex-col items-center gap-0.5 py-2 px-3 ${activeSection === tab.id ? 'text-teal-600' : 'text-gray-400'}`}>
              <tab.icon size={20} />
              <span className="text-[10px] font-medium">{tab.label}</span>
            </button>
          ))}
        </div>
      </nav>

      {/* Video Room Modal */}
      {showVideoRoom && videoRoomData && (
        <VideoRoom roomName={videoRoomData.room_name} token={videoRoomData.token} role="patient" onEnd={() => { setShowVideoRoom(false); setVideoRoomData(null) }} />
      )}
    </div>
  )
}
