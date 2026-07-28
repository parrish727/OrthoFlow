import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Send, User, Clock, Filter, Inbox, Mail, ArrowLeft } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

// --- Types ---

interface MessageThread {
  patient_id: string
  patient_name: string
  last_message: string
  last_message_at: string
  unread_count: number
  category: 'medical' | 'appointment' | 'general'
}

interface ThreadMessage {
  id: string
  patient_id: string
  direction: 'inbound' | 'outbound'
  subject: string | null
  body: string
  is_read: boolean
  sender_name: string
  created_at: string
}

type FilterTab = 'all' | 'unread' | 'medical' | 'appointments'

// --- Utilities ---

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
  const isThisYear = d.getFullYear() === now.getFullYear()
  if (isThisYear) {
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric', year: 'numeric' })
}

function truncatePreview(text: string, maxLength: number = 60): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trimEnd() + '…'
}

// --- Filter Tabs ---

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'unread', label: 'Unread' },
  { key: 'medical', label: 'Medical' },
  { key: 'appointments', label: 'Appointments' },
]

// --- Main Component ---

export default function PatientMessages() {
  const { userId } = useAuth()

  // State
  const [threads, setThreads] = useState<MessageThread[]>([])
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ThreadMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [activeFilter, setActiveFilter] = useState<FilterTab>('all')
  const [loadingThreads, setLoadingThreads] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [sending, setSending] = useState(false)
  const [mobileShowConversation, setMobileShowConversation] = useState(false)

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // --- Data Fetching ---

  const fetchThreads = useCallback(async () => {
    try {
      const filterParam = activeFilter === 'all' ? undefined : activeFilter
      const res = await api.getPatientMessageThreads(filterParam ? { filter: filterParam } : undefined)
      if (res.ok) {
        const data = await res.json()
        const rawThreads = data.threads || data.items || []
        // Map API fields to component interface
        setThreads(rawThreads.map((t: Record<string, unknown>) => ({
          patient_id: t.patient_id,
          patient_name: t.patient_name,
          last_message: t.last_message_body || t.last_message || '',
          last_message_at: t.last_message_at || '',
          unread_count: t.unread_count || 0,
          category: 'general' as const,
        })))
      }
    } catch {
      // silent
    } finally {
      setLoadingThreads(false)
    }
  }, [activeFilter])

  const fetchMessages = useCallback(async (patientId: string) => {
    setLoadingMessages(true)
    try {
      const res = await api.getPatientMessageThread(patientId)
      if (res.ok) {
        const data = await res.json()
        const rawMessages = data.messages || []
        setMessages(rawMessages.map((m: Record<string, unknown>) => ({
          id: m.id,
          patient_id: m.patient_id,
          direction: m.direction === 'from_patient' ? 'inbound' : 'outbound',
          subject: m.subject || null,
          body: m.body || '',
          is_read: m.is_read ?? true,
          sender_name: m.direction === 'from_patient' ? (m.patient_name || 'Patient') : 'Staff',
          created_at: m.created_at || '',
        })))
      }
    } catch {
      // silent
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  // --- Effects ---

  useEffect(() => {
    fetchThreads()
  }, [fetchThreads])

  useEffect(() => {
    if (selectedPatientId) {
      fetchMessages(selectedPatientId)
      // Mark thread as read
      api.markThreadRead(selectedPatientId).catch(() => {})
    }
  }, [selectedPatientId, fetchMessages])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Poll for new messages every 5s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchThreads()
      if (selectedPatientId) {
        fetchMessages(selectedPatientId)
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchThreads, fetchMessages, selectedPatientId])

  // --- Handlers ---

  function handleSelectThread(patientId: string) {
    setSelectedPatientId(patientId)
    setMobileShowConversation(true)
    // Update unread count locally
    setThreads(prev =>
      prev.map(t => t.patient_id === patientId ? { ...t, unread_count: 0 } : t)
    )
  }

  function handleBackToThreads() {
    setMobileShowConversation(false)
  }

  async function handleSend() {
    if (!inputText.trim() || !selectedPatientId || sending) return

    const body = inputText.trim()
    setInputText('')
    setSending(true)

    // Optimistic update
    const optimisticMessage: ThreadMessage = {
      id: `temp-${Date.now()}`,
      patient_id: selectedPatientId,
      direction: 'outbound',
      subject: null,
      body,
      is_read: true,
      sender_name: 'You',
      created_at: new Date().toISOString(),
    }
    setMessages(prev => [...prev, optimisticMessage])

    try {
      const res = await api.sendPatientMessage(selectedPatientId, { body })
      if (res.ok) {
        // Refresh to get server-generated ID
        fetchMessages(selectedPatientId)
        fetchThreads()
      }
    } catch {
      // Remove optimistic message on failure
      setMessages(prev => prev.filter(m => m.id !== optimisticMessage.id))
    } finally {
      setSending(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  // --- Filtered Threads ---

  const filteredThreads = threads

  // --- Selected Thread Info ---

  const selectedThread = threads.find(t => t.patient_id === selectedPatientId)

  // --- Render ---

  return (
    <div className="h-[calc(100vh-7.5rem)] flex rounded-2xl border border-gray-200/80 bg-white shadow-sm overflow-hidden">
      {/* Thread List — Left Panel */}
      <div
        className={`w-full md:w-[350px] md:min-w-[350px] flex flex-col border-r border-gray-200 bg-gray-50 ${
          mobileShowConversation ? 'hidden md:flex' : 'flex'
        }`}
      >
        {/* Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <Mail size={18} className="text-teal-600" />
            <h2 className="text-sm font-semibold text-gray-900">Patient Messages</h2>
          </div>
          <div className="flex items-center gap-1">
            <Filter size={16} className="text-gray-400" />
          </div>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1 px-3 py-2 border-b border-gray-100">
          {FILTER_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => {
                setActiveFilter(tab.key)
                setLoadingThreads(true)
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                activeFilter === tab.key
                  ? 'bg-teal-500 text-white'
                  : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Thread List */}
        <div className="flex-1 overflow-y-auto">
          {loadingThreads ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <div className="w-6 h-6 border-2 border-gray-300 border-t-teal-500 rounded-full animate-spin" />
              <span className="text-xs mt-2">Loading…</span>
            </div>
          ) : filteredThreads.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <Inbox size={32} className="mb-2" />
              <span className="text-sm">No messages</span>
              <span className="text-xs mt-1">Patient messages will appear here</span>
            </div>
          ) : (
            filteredThreads.map(thread => (
              <ThreadItem
                key={thread.patient_id}
                thread={thread}
                isActive={thread.patient_id === selectedPatientId}
                onClick={() => handleSelectThread(thread.patient_id)}
              />
            ))
          )}
        </div>
      </div>

      {/* Conversation — Right Panel */}
      <div
        className={`flex-1 flex flex-col ${
          mobileShowConversation ? 'flex' : 'hidden md:flex'
        }`}
      >
        {selectedPatientId && selectedThread ? (
          <>
            {/* Conversation Header */}
            <div className="h-14 flex items-center gap-3 px-4 border-b border-gray-200 bg-white">
              {/* Mobile back button */}
              <button
                onClick={handleBackToThreads}
                className="md:hidden p-1.5 -ml-1 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                aria-label="Back to threads"
              >
                <ArrowLeft size={18} />
              </button>
              <div className="w-8 h-8 rounded-full bg-teal-100 flex items-center justify-center flex-shrink-0">
                <User size={16} className="text-teal-700" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-gray-900 truncate">{selectedThread.patient_name}</p>
                <p className="text-xs text-gray-500 truncate">
                  {selectedThread.category === 'medical' ? 'Medical' :
                   selectedThread.category === 'appointment' ? 'Appointment' : 'General'}
                </p>
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {loadingMessages ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <div className="w-6 h-6 border-2 border-gray-300 border-t-teal-500 rounded-full animate-spin" />
                </div>
              ) : messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-gray-400">
                  <MessageSquare size={32} className="mb-2" />
                  <span className="text-sm">No messages yet</span>
                  <span className="text-xs mt-1">Start the conversation below</span>
                </div>
              ) : (
                messages.map(msg => (
                  <MessageBubble key={msg.id} message={msg} isOwn={msg.direction === 'outbound'} />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Compose Bar */}
            <div className="border-t border-gray-200 bg-white px-4 py-3">
              <div className="flex items-center gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={e => setInputText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a reply…"
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim() || sending}
                  className="p-2.5 rounded-lg bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  aria-label="Send message"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          </>
        ) : (
          /* Empty State — No Thread Selected */
          <div className="flex-1 flex flex-col items-center justify-center py-12 text-gray-400">
            <MessageSquare size={48} className="mb-3" />
            <p className="text-sm font-medium text-gray-500">Select a conversation</p>
            <p className="text-xs mt-1">Choose a patient thread from the left to view messages</p>
          </div>
        )}
      </div>
    </div>
  )
}

// --- Internal Sub-Components ---

function ThreadItem({
  thread,
  isActive,
  onClick,
}: {
  thread: MessageThread
  isActive: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-4 py-3 border-b border-gray-100 transition-colors hover:bg-white ${
        isActive ? 'bg-white border-l-2 border-l-teal-500' : ''
      }`}
    >
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 mt-0.5">
          <User size={16} className="text-gray-500" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <span className={`text-sm truncate ${thread.unread_count > 0 ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'}`}>
              {thread.patient_name}
            </span>
            <span className="text-xs text-gray-400 flex-shrink-0 flex items-center gap-1">
              <Clock size={10} />
              {formatTime(thread.last_message_at)}
            </span>
          </div>
          <div className="flex items-center justify-between gap-2 mt-0.5">
            <span className={`text-xs truncate ${thread.unread_count > 0 ? 'text-gray-700' : 'text-gray-500'}`}>
              {truncatePreview(thread.last_message)}
            </span>
            {thread.unread_count > 0 && (
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-teal-500 text-white text-[10px] font-bold flex items-center justify-center">
                {thread.unread_count > 9 ? '9+' : thread.unread_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  )
}

function MessageBubble({ message, isOwn }: { message: ThreadMessage; isOwn: boolean }) {
  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[75%] ${isOwn ? 'order-1' : ''}`}>
        {/* Sender label */}
        <p className={`text-[10px] mb-1 ${isOwn ? 'text-right text-gray-400' : 'text-left text-gray-400'}`}>
          {message.sender_name}
        </p>
        {/* Subject line if present */}
        {message.subject && (
          <p className={`text-[11px] font-medium mb-0.5 ${isOwn ? 'text-right text-teal-100' : 'text-left text-gray-600'}`}>
            {message.subject}
          </p>
        )}
        {/* Bubble */}
        <div
          className={`px-3.5 py-2.5 text-sm leading-relaxed ${
            isOwn
              ? 'bg-teal-500 text-white rounded-2xl rounded-br-md'
              : 'bg-white text-gray-900 border border-gray-100 rounded-2xl rounded-bl-md'
          }`}
        >
          {message.body}
        </div>
        {/* Timestamp */}
        <p className={`text-[10px] mt-1 text-gray-400 ${isOwn ? 'text-right' : 'text-left'}`}>
          {formatTime(message.created_at)}
        </p>
      </div>
    </div>
  )
}
