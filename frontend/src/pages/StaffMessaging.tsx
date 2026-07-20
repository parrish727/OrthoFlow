import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageSquare, Send, Plus, Smile, Users, X, Hash } from 'lucide-react'
import { api } from '../lib/api'
import { useAuth } from '../hooks/useAuth'

// --- Types ---

interface ChatRoom {
  id: string
  name: string
  room_type: 'general' | 'direct' | 'group'
  last_message?: string
  last_message_at?: string
  unread_count?: number
}

interface ChatMessage {
  id: string
  room_id: string
  sender_id: string
  sender_name: string
  content: string
  message_type: 'text' | 'emoji' | 'system'
  created_at: string
}

interface TeamMember {
  id: string
  full_name: string
  role: string
}

// --- Constants ---

const EMOJI_GRID = ['😀', '😂', '❤️', '👍', '🙏', '🔥', '💯', '✅', '❌', '🦷']

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function getWsUrl(roomId: string, token: string): string {
  const base = API_URL.replace(/^http/, 'ws')
  return `${base}/api/v1/chat/ws/${roomId}?token=${token}`
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

// --- Component ---

export default function DAMessaging() {
  const { userId } = useAuth()
  const token = localStorage.getItem('token') || ''

  // State
  const [rooms, setRooms] = useState<ChatRoom[]>([])
  const [selectedRoomId, setSelectedRoomId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [inputText, setInputText] = useState('')
  const [showEmoji, setShowEmoji] = useState(false)
  const [typingUser, setTypingUser] = useState<string | null>(null)
  const [loadingRooms, setLoadingRooms] = useState(true)
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(true)

  // Refs
  const wsRef = useRef<WebSocket | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const typingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastTypingSentRef = useRef<number>(0)

  // --- Fetch Rooms ---
  const fetchRooms = useCallback(async () => {
    try {
      const res = await api.request('/api/v1/chat/rooms')
      if (res.ok) {
        const data = await res.json()
        setRooms(Array.isArray(data) ? data : data.rooms || [])
      }
    } catch {
      // silent
    } finally {
      setLoadingRooms(false)
    }
  }, [])

  useEffect(() => {
    fetchRooms()
  }, [fetchRooms])

  // --- Fetch Messages for Selected Room ---
  const fetchMessages = useCallback(async (roomId: string) => {
    try {
      const res = await api.request(`/api/v1/chat/rooms/${roomId}/messages?limit=50`)
      if (res.ok) {
        const data = await res.json()
        const msgList = Array.isArray(data) ? data : data.messages || []
        // API returns newest-first, reverse for display (oldest at top)
        const sorted = [...msgList].reverse()
        setMessages(sorted)
      }
    } catch {
      // silent
    } finally {
      setLoadingMessages(false)
    }
  }, [])

  // --- WebSocket Connection ---
  useEffect(() => {
    if (!selectedRoomId || !token) return

    // Close previous connection
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const ws = new WebSocket(getWsUrl(selectedRoomId, token))
    wsRef.current = ws

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'message') {
          const msg: ChatMessage = {
            id: data.id || crypto.randomUUID(),
            room_id: selectedRoomId,
            sender_id: data.sender_id,
            sender_name: data.sender_name,
            content: data.content,
            message_type: data.message_type || 'text',
            created_at: data.created_at || new Date().toISOString(),
          }
          setMessages((prev) => [...prev, msg])
          setTypingUser(null)
        } else if (data.type === 'typing') {
          setTypingUser(data.sender_name)
          if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current)
          typingTimeoutRef.current = setTimeout(() => setTypingUser(null), 3000)
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      wsRef.current = null
    }

    return () => {
      ws.close()
      wsRef.current = null
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current)
    }
  }, [selectedRoomId, token])

  // --- Auto-scroll on new messages ---
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // --- Select Room ---
  function handleSelectRoom(roomId: string) {
    setSelectedRoomId(roomId)
    setMessages([])
    setTypingUser(null)
    setShowEmoji(false)
    setMobileSidebarOpen(false)
    setLoadingMessages(true)
    fetchMessages(roomId)
  }

  // --- Poll for new messages (iMessage-style: always up to date) ---
  useEffect(() => {
    if (!selectedRoomId) return
    const interval = setInterval(() => {
      fetchMessages(selectedRoomId)
    }, 3000)
    return () => clearInterval(interval)
  }, [selectedRoomId, fetchMessages])

  // --- Send Typing Indicator ---
  function sendTypingIndicator() {
    const now = Date.now()
    if (now - lastTypingSentRef.current < 2000) return
    lastTypingSentRef.current = now
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'typing' }))
    }
  }

  // --- Send Message ---
  async function handleSend() {
    const text = inputText.trim()
    if (!text || !selectedRoomId) return

    setInputText('')
    setShowEmoji(false)

    // Send via REST (persists and broadcasts via WebSocket)
    try {
      const res = await api.request(`/api/v1/chat/rooms/${selectedRoomId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: text, message_type: 'text' }),
      })
      if (res.ok) {
        const msg = await res.json()
        // Optimistically add to local state so user sees their message immediately
        setMessages((prev) => {
          // Avoid duplicate if WebSocket already delivered it
          if (prev.some((m) => m.id === msg.id)) return prev
          return [...prev, {
            id: msg.id,
            room_id: selectedRoomId,
            sender_id: msg.sender_id,
            sender_name: msg.sender_name,
            content: msg.content,
            message_type: msg.message_type || 'text',
            is_edited: false,
            created_at: msg.created_at,
          }]
        })
        // Re-fetch handled by polling interval — auto-replies appear within 3s
      }
    } catch {
      // If REST fails, try WebSocket as fallback
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'message', content: text }))
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function insertEmoji(emoji: string) {
    setInputText((prev) => prev + emoji)
    setShowEmoji(false)
  }

  // --- Render ---
  const selectedRoom = rooms.find((r) => r.id === selectedRoomId)

  return (
    <div className="flex h-[calc(100vh-7.5rem)] rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
      {/* Left Sidebar — Room List */}
      <aside
        className={`${
          mobileSidebarOpen ? 'flex' : 'hidden'
        } md:flex flex-col w-full md:w-72 lg:w-80 border-r border-gray-200 bg-gray-50 flex-shrink-0`}
      >
        {/* Sidebar Header */}
        <div className="h-14 flex items-center justify-between px-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <MessageSquare size={18} className="text-teal-600" />
            <h2 className="text-sm font-semibold text-gray-900">DA Chat</h2>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="p-1.5 rounded-md text-gray-500 hover:text-teal-600 hover:bg-teal-50 transition-colors"
            aria-label="Create room"
          >
            <Plus size={18} />
          </button>
        </div>

        {/* Room List */}
        <div className="flex-1 overflow-y-auto">
          {loadingRooms ? (
            <div className="flex items-center justify-center h-32 text-sm text-gray-400">
              Loading rooms…
            </div>
          ) : rooms.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 text-sm text-gray-400 px-4 text-center">
              <Users size={24} className="mb-2 text-gray-300" />
              No rooms yet. Create one to get started.
            </div>
          ) : (
            rooms.map((room) => (
              <button
                key={room.id}
                onClick={() => handleSelectRoom(room.id)}
                className={`w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-white transition-colors ${
                  selectedRoomId === room.id ? 'bg-white border-l-2 border-l-teal-500' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 min-w-0">
                    <Hash size={14} className="text-gray-400 flex-shrink-0" />
                    <span className="text-sm font-medium text-gray-900 truncate">
                      {room.name}
                    </span>
                  </div>
                  {room.unread_count && room.unread_count > 0 ? (
                    <span className="ml-2 flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-teal-500 text-white text-[10px] font-bold">
                      {room.unread_count > 9 ? '9+' : room.unread_count}
                    </span>
                  ) : null}
                </div>
                {room.last_message && (
                  <p className="text-xs text-gray-500 truncate mt-0.5 pl-5">
                    {room.last_message}
                  </p>
                )}
                {room.last_message_at && (
                  <p className="text-[10px] text-gray-400 mt-0.5 pl-5">
                    {formatTime(room.last_message_at)}
                  </p>
                )}
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Right Panel — Message View */}
      <div
        className={`${
          mobileSidebarOpen ? 'hidden' : 'flex'
        } md:flex flex-col flex-1 min-w-0`}
      >
        {!selectedRoom ? (
          // Empty state
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400">
            <MessageSquare size={40} className="mb-3 text-gray-200" />
            <p className="text-sm">Select a room to start chatting</p>
          </div>
        ) : (
          <>
            {/* Room Header */}
            <div className="h-14 flex items-center px-4 border-b border-gray-200 flex-shrink-0">
              <button
                onClick={() => setMobileSidebarOpen(true)}
                className="md:hidden mr-3 p-1 text-gray-500 hover:text-gray-700"
                aria-label="Back to rooms"
              >
                ←
              </button>
              <Hash size={16} className="text-gray-400 mr-2" />
              <h3 className="text-sm font-semibold text-gray-900 truncate">
                {selectedRoom.name}
              </h3>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {loadingMessages ? (
                <div className="flex items-center justify-center h-32 text-sm text-gray-400">
                  Loading messages…
                </div>
              ) : messages.length === 0 ? (
                <div className="flex items-center justify-center h-32 text-sm text-gray-400">
                  No messages yet. Say hello! 👋
                </div>
              ) : (
                messages.map((msg) => {
                  const isOwn = msg.sender_id === userId
                  const isSystem = msg.message_type === 'system'

                  if (isSystem) {
                    return (
                      <div key={msg.id} className="text-center">
                        <span className="text-xs text-gray-400 italic">{msg.content}</span>
                      </div>
                    )
                  }

                  return (
                    <div
                      key={msg.id}
                      className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[75%] rounded-xl px-3 py-2 ${
                          isOwn
                            ? 'bg-teal-500 text-white rounded-br-sm'
                            : 'bg-gray-100 text-gray-900 rounded-bl-sm'
                        }`}
                      >
                        {!isOwn && (
                          <p className="text-[10px] font-semibold text-teal-700 mb-0.5">
                            {msg.sender_name}
                          </p>
                        )}
                        <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                        <p
                          className={`text-[10px] mt-1 ${
                            isOwn ? 'text-teal-100' : 'text-gray-400'
                          }`}
                        >
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                    </div>
                  )
                })
              )}

              {/* Typing Indicator */}
              {typingUser && (
                <div className="flex items-center gap-1 text-xs text-gray-400 italic">
                  <span>{typingUser} is typing</span>
                  <span className="animate-pulse">…</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="border-t border-gray-200 px-4 py-3 flex-shrink-0">
              {/* Emoji Picker */}
              {showEmoji && (
                <div className="mb-2 p-2 bg-gray-50 rounded-lg border border-gray-200 flex flex-wrap gap-1">
                  {EMOJI_GRID.map((emoji) => (
                    <button
                      key={emoji}
                      onClick={() => insertEmoji(emoji)}
                      className="w-8 h-8 flex items-center justify-center text-lg rounded hover:bg-gray-200 transition-colors"
                      aria-label={`Insert ${emoji}`}
                    >
                      {emoji}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowEmoji(!showEmoji)}
                  className={`p-2 rounded-md transition-colors ${
                    showEmoji
                      ? 'text-teal-600 bg-teal-50'
                      : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
                  }`}
                  aria-label="Toggle emoji picker"
                >
                  <Smile size={18} />
                </button>
                <input
                  type="text"
                  value={inputText}
                  onChange={(e) => {
                    setInputText(e.target.value)
                    sendTypingIndicator()
                  }}
                  onKeyDown={handleKeyDown}
                  placeholder="Type a message…"
                  className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                />
                <button
                  onClick={handleSend}
                  disabled={!inputText.trim()}
                  className="p-2 rounded-md bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  aria-label="Send message"
                >
                  <Send size={18} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Create Room Modal */}
      {showCreateModal && (
        <CreateRoomModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(room) => {
            setRooms((prev) => [room, ...prev])
            setShowCreateModal(false)
            handleSelectRoom(room.id)
          }}
        />
      )}
    </div>
  )
}

// --- Create Room Modal ---

interface CreateRoomModalProps {
  onClose: () => void
  onCreated: (room: ChatRoom) => void
}

function CreateRoomModal({ onClose, onCreated }: CreateRoomModalProps) {
  const [name, setName] = useState('')
  const [roomType, setRoomType] = useState<'general' | 'group'>('general')
  const [members, setMembers] = useState<TeamMember[]>([])
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingMembers, setLoadingMembers] = useState(true)

  useEffect(() => {
    async function loadTeam() {
      try {
        const res = await api.request('/api/v1/team/')
        if (res.ok) {
          const data = await res.json()
          const staffList = data.staff || data.members || []
          setMembers(Array.isArray(staffList) ? staffList : [])
        }
      } catch {
        // silent
      } finally {
        setLoadingMembers(false)
      }
    }
    loadTeam()
  }, [])

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    try {
      const res = await api.request('/api/v1/chat/rooms', {
        method: 'POST',
        body: JSON.stringify({
          name: name.trim(),
          room_type: roomType,
          member_ids: selectedMemberIds,
        }),
      })
      if (res.ok) {
        const room = await res.json()
        onCreated(room)
      }
    } catch {
      // silent
    } finally {
      setLoading(false)
    }
  }

  function toggleMember(id: string) {
    setSelectedMemberIds((prev) =>
      prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Create Chat Room</h3>
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600"
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        {/* Room Name */}
        <label className="block text-sm font-medium text-gray-700 mb-1">Room Name</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Front Desk Chat"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent mb-4"
          maxLength={100}
        />

        {/* Room Type */}
        <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setRoomType('general')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              roomType === 'general'
                ? 'bg-teal-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            General
          </button>
          <button
            onClick={() => setRoomType('group')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              roomType === 'group'
                ? 'bg-teal-500 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}
          >
            Group
          </button>
        </div>

        {/* Member Selection */}
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Members ({selectedMemberIds.length} selected)
        </label>
        <div className="max-h-40 overflow-y-auto border border-gray-200 rounded-lg mb-4">
          {loadingMembers ? (
            <p className="text-sm text-gray-400 p-3 text-center">Loading team…</p>
          ) : members.length === 0 ? (
            <p className="text-sm text-gray-400 p-3 text-center">No team members found</p>
          ) : (
            members.map((m) => (
              <label
                key={m.id}
                className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selectedMemberIds.includes(m.id)}
                  onChange={() => toggleMember(m.id)}
                  className="rounded border-gray-300 text-teal-500 focus:ring-teal-500"
                />
                <span className="text-sm text-gray-900">{m.full_name}</span>
                <span className="text-xs text-gray-400 ml-auto">{m.role}</span>
              </label>
            ))
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim() || loading}
            className="px-4 py-2 rounded-lg bg-teal-500 text-white text-sm font-medium hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Creating…' : 'Create Room'}
          </button>
        </div>
      </div>
    </div>
  )
}
